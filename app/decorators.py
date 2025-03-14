from functools import wraps
from typing import Callable, Optional, Dict, Any, List, Tuple
from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
import inspect
import mysql.connector
from mysql.connector import pooling
import secrets
import hashlib
import uuid
import time
import json
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio

from database import (
    get_session,
    get_user_by_id,
    extend_session
)

SESSION_EXPIRY_HOURS = 24

def auth_required(func: Callable) -> Callable:
    """
    Universal authentication decorator for FastAPI route handlers.
    Works with both sync and async functions.
    
    Usage:
    ```
    @app.get("/protected")
    @auth_required
    def protected_route(request: Request):
        return {"message": "This is a protected route"}
    
    @app.get("/protected-async")
    @auth_required
    async def protected_async_route(request: Request):
        return {"message": "This is a protected async route"}
    ```
    """
    is_async = inspect.iscoroutinefunction(func)
    
    if is_async:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request and 'request' in kwargs:
                request = kwargs['request']
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found in function arguments")
            
            # Get response from kwargs or create new one
            response = kwargs.get('response', None)
            
            redirect = RedirectResponse("/login")

            # Check if user is authenticated
            sessionId = request.cookies.get("sessionId")
            if not sessionId:
                return redirect
            
            session = await get_session(sessionId)
            if not session:
                return redirect
            
            # Handle expired session
            lastAccess = session.get("last_access")
            expiry_threshold = expiry_threshold = datetime.now() - timedelta(hours=SESSION_EXPIRY_HOURS)
            if lastAccess < expiry_threshold:
                return RedirectResponse("/login")

            user = await get_user_by_id(session.get("user_id"))
            if not user:
                return redirect

            # Set user in request state for later access
            request.state.username = str(user.get("username"))
            request.state.userId = user.get("id")
            
            # Extend session
            await extend_session(sessionId)
            
            # Continue with the original function
            return await func(*args, **kwargs)
        
        return wrapper
    else:
        @wraps(func)
        async def sync_wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request and 'request' in kwargs:
                request = kwargs['request']
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found in function arguments")
            
            # Get response from kwargs or create new one
            response = kwargs.get('response', None)
            
            redirect = RedirectResponse("/login")

            # Check if user is authenticated
            sessionId = request.cookies.get("sessionId")
            if not sessionId:
                return redirect
            
            loop = asyncio.get_event_loop()
            try:
                session = loop.run_until_complete(asyncio.to_thread(get_session, sessionId))
                if not session:
                    return redirect
                
                user = loop.run_until_complete(asyncio.to_thread(get_user_by_id, session.get("user_id")))
                if not user:
                    return redirect
                
                request.state.username = str(user.get("username"))
                request.state.userId = str(user.get("id"))
                
                # Extend session
                loop.run_until_complete(asyncio.to_thread(extend_session, sessionId))

                # Continue with the original function
                return func(*args, **kwargs)
            finally:
                loop.close()
        
        return sync_wrapper


