from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
from typing import Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import uuid
import os
import requests
import json
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

from decorators import auth_required
from database import (
    setup_database,

    get_user_by_id,
    get_user_by_username,
    update_user_by_id,
    create_user,
    delete_user_by_id,
   
    create_session,
    get_session,
    delete_session_by_id,
    delete_session_by_user_id,

    get_sensor_by_id,
    get_sensors_by_user_id,
    add_sensor,
    update_sensor,
    delete_sensor,

    get_clothes_by_id,
    get_clothes_by_user_id,
    add_clothes,
    update_clothes,
    delete_clothes,

    get_data_by_sensor_id,
    add_data,
    get_recent_data
)

load_dotenv()
API_KEY = os.getenv('API_KEY')

INIT_USERS = [
    ("nathan", "password", "email", "San Diego"),
    ("user", "pwd", "gmail", "New York")
]
INIT_SENSORS = [
    (1, "Temperature", "Celsius", "8C:4F:00:37:55:00"),
    (2, "Pressure", "Pascals", "asdf.com"),
]
INIT_CLOTHES = [
    (1, "Black Shirt 1", "shirt", "./static/shirt.png"),
    (2, "Black Shirt 2", "shirt", "./static/shirt.png"),
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for managing application startup and shutdown.
    Handles database setup and cleanup in a more structured way.
    """
    # Startup: Setup resources
    try:
        await setup_database(INIT_USERS)  # Make sure setup_database is async
        for user_id, type, units, address in INIT_SENSORS:
            await add_sensor(user_id, type, units, address)
        print("Added sensors successfully")
        
        for user_id, name, type, image_address in INIT_CLOTHES:
            await add_clothes(user_id, name, type, image_address)
        print("Added clothes successfully")

        print("Database setup completed")
        yield
    finally:
        print("Shutdown completed")

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


def serve_content(file: str, username: str):
    with open(file) as html:
        return html.read().replace("{username}", username)


''' API Routes '''
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # accept the websocket connection
    await websocket.accept()

    subscribed_sensors = []

    async def get_all_recent_data():
        nonlocal subscribed_sensors
        data = {}
        for sensor_id in subscribed_sensors:
            data[sensor_id] = await get_recent_data(sensor_id)
            if data[sensor_id]:
                data[sensor_id]['timestamp'] = data[sensor_id]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

        return data

    try:
        subscribed_sensors = await websocket.receive_json()
        while True:
            if subscribed_sensors:
                data = await get_all_recent_data()
                if data:
                    await websocket.send_json(data)
                await asyncio.sleep(3)
    except Exception as e:
        print(e)
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
    return


@app.get("/api/sensors/{sensor_id}")
@auth_required
async def get_sensor(request: Request, sensor_id: str):
    sensor = await get_sensor_by_id(sensor_id)

    if sensor.get("user_id") != request.state.userId:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return sensor

@app.get("/api/sensors")
@auth_required
async def get_sensors(request: Request):
    return await get_sensors_by_user_id(request.state.userId)

class SensorModel(BaseModel):
    type: str
    units: str
    address: str

@app.post("/api/sensors")
@auth_required
async def post_sensor(request: Request, data: SensorModel):
    sensor = await add_sensor(request.state.userId, data.type, data.units, data.address)
    if sensor:
        return JSONResponse(content=sensor, status_code=201)
    else:
        return Response(content="Error", status_code=400)
    

class UpdateSensorModel(BaseModel):
    type: Optional[str] = None
    units: Optional[str] = None
    address: Optional[str] = None

@app.put("/api/sensors/{sensor_id}")
@auth_required
async def put_sensor(request: Request, sensor_id: str, data: UpdateSensorModel):
    sensor = await get_sensor_by_id(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Not Found")

    if request.state.userId != sensor.get("user_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if await update_sensor(sensor_id, data.type, data.units, data.address):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Server Error", status_code=400)

@app.delete("/api/sensors/{sensor_id}")
@auth_required
async def delete(request: Request, sensor_id: str):
    sensor = await get_sensor_by_id(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Not Found")

    if request.state.userId != sensor.get("user_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if await delete_sensor(sensor_id):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Server Error", status_code=400)


@app.get("/api/user/{username}")
@auth_required
async def get_user(request: Request, username: str):
    if username != request.state.username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = await get_user_by_username(username)
    if user:
        return user
    else:
        return Response(content="Not Found", status_code=404)


@app.get("/api/user")
@auth_required
async def get_user(request: Request):
    if not request.state.username:
        raise HTTPException(status_code=404, detail="Not Found")
    
    user = await get_user_by_username(request.state.username)
    if not user:
        raise HTTPException(status_code=404, detail="Not Found")
    
    return user



class UpdateUserModel(BaseModel):
    new_username: Optional[str] = None
    new_password: Optional[str] = None
    new_email: Optional[str] = None
    new_location: Optional[str] = None

@app.put("/api/user")
@auth_required
async def put_user(request: Request, data: UpdateUserModel):
    if await update_user_by_id(request.state.userId, data.new_username, data.new_password, data.new_email, data.new_location):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Not Found", status_code=404)

@app.delete("/api/user")
@auth_required
async def delete_user(request: Request):    
    if await delete_user_by_id(request.state.userId):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Not Found", status_code=404)


@app.get("/api/clothes/{clothes_id}")
@auth_required
async def get_clothes(request: Request, clothes_id: str):
    clothes = await get_clothes_by_id(clothes_id)
    if not clothes:
        raise HTTPException(status_code=404, detail="Not Found")

    if request.state.userId != clothes.get("user_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return clothes

@app.get("/api/clothes")
@auth_required
async def get_clothes(request: Request):
    clothes = await get_clothes_by_user_id(request.state.userId)
    if clothes == None:
        raise HTTPException(status_code=404, detail="Not Found")

    return clothes

class ClothesModel(BaseModel):
    name: str
    type: str
    image_address: str

@app.post("/api/clothes")
@auth_required
async def post_clothes(request: Request, data: ClothesModel):
    clothes = await add_clothes(request.state.userId, data.name, data.type, data.image_address)
    if clothes:
        return JSONResponse(content=clothes, status_code=201)
    else:
        return Response(content="Error", status_code=400)

class UpdateClothesModel(BaseModel):
    name: Optional[str]
    type: Optional[str]
    image_address: Optional[str]

@app.put("/api/clothes/{clothes_id}")
@auth_required
async def put_clothes(request: Request, clothes_id: str, data: UpdateClothesModel):
    clothes = await get_clothes_by_id(clothes_id)
    if not clothes:
        raise HTTPException(status_code=404, detail="Not Found")

    if request.state.userId != clothes.get("user_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if await update_clothes(clothes_id, data.name, data.type, data.image_address):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Not Found", status_code=404)
    
@app.delete("/api/clothes/{clothes_id}")
@auth_required
async def delete(request: Request, clothes_id: str):
    clothes = await get_clothes_by_id(clothes_id)
    if not clothes:
        raise HTTPException(status_code=404, detail="Not Found")

    if request.state.userId != clothes.get("user_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if await delete_clothes(clothes_id):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Not Found", status_code=404)


class SensorDataModel(BaseModel):
    value: float
    type: str
    address: str
    api_key: str

@app.post("/api/data")
async def post(data: SensorDataModel):
    if data.api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if await add_data(data.value, data.type, data.address):
        return Response(content="Success", status_code=200)
    else:
        return Response(content="Error", status_code=400)


@app.get("/api/ai-wardrobe-recommendation")
@auth_required
async def get(request: Request):
    if not request.state.userId:
        raise HTTPException(status_code=404, detail="Not Found")
    
    user = await get_user_by_id(request.state.userId)
    if not user:
        raise HTTPException(status_code=404, detail="Not Found")
    
    userLocation = user.get('location')
    clothes = await get_clothes_by_user_id(request.state.userId)
    try:
        geolocator = Nominatim(user_agent="wardrobify-ece140a")
        location = geolocator.geocode(userLocation)

        dataResponse = requests.get(f"https://api.weather.gov/points/{location.latitude},{location.longitude}")
        data = dataResponse.json()

        forecastUrl = data.get('properties').get('forecast')

        currentForecastResponse = requests.get(forecastUrl)
        currentForecast = currentForecastResponse.json().get('properties').get('periods')[0]

        query = f'''
        Pick an outfit for me.
        My wardrobe consists of the following items: {clothes}.
        The weather conditions today: {currentForecast.get('shortForecast')}, temperature: {currentForecast.get('temperature')}F.
        Do not use markdown for you response, only use plaintext.
        Format your response in the following way (omit lines if there are not that many choices, add lines if there are more):
        [Clothing 1 Name] - [Clothing 1 Type]
        [Clothing 2 Name] - [Clothing 2 Type]
        [Clothing 3 Name] - [Clothing 3 Type]
        etc.
        Reasoning: [Reason for choices]
        '''

        EMAIL = os.getenv('EMAIL')
        STUDENT_ID = os.getenv('STUDENT_ID')

        print(EMAIL)
        print(STUDENT_ID)

        if not EMAIL or not STUDENT_ID:
            return

        recommendationResponse = requests.post('https://ece140-wi25-api.frosty-sky-f43d.workers.dev/api/v1/ai/complete',
                        headers={
                        'accept': 'application/json',
                        'email': EMAIL,
                        'pid': STUDENT_ID,
                        'Content-Type': 'application/json'
                        },
                        json={"prompt": query})
        

        print(recommendationResponse.json())

        return recommendationResponse.json().get('result')
    
    except Exception as e:
        print(e)
        return {'response': 'Error fetching AI response'}


'''Session Routes'''
class LoginModel(BaseModel):
    username: str
    password: str

@app.post("/login")
async def post(data: LoginModel):

    unauthorized = HTTPException(status_code=401, detail="Unauthorized")
    
    if not data.username or not data.password:
        raise unauthorized
    
    user = await get_user_by_username(data.username)
    if not user:
       raise unauthorized

    if data.password != user.get("password"):
       raise unauthorized
    
    sessionId = str(uuid.uuid4())
    userId = str(user.get("id"))

    await delete_session_by_user_id(userId)
    
    await create_session(userId, sessionId)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(key="sessionId", value=sessionId)
    return response


class SignupModel(BaseModel):
    username: str
    password: str
    email: str
    location: str

@app.post("/signup")
async def post(data: SignupModel):
    if not data.username or not data.password or not data.email or not data.location:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    userId = await create_user(data.username, data.password, data.email, data.location)
    if not userId:
        raise HTTPException(status_code=409, detail="Unable to create user")
    
    sessionId = str(uuid.uuid4())

    await create_session(userId, sessionId)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(key="sessionId", value=sessionId)
    return response


@app.post("/logout")
async def logout(request: Request):
    """Clear session and redirect to login page"""

    # Delete session on logout
    sessionId = request.cookies.get("sessionId")
    if sessionId:
        await delete_session_by_id(sessionId)

    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(key="sessionId")
    return response


'''Document Routes '''
@app.get("/", response_class=HTMLResponse)
async def get_html(request: Request) -> HTMLResponse:
    sessionId = request.cookies.get("sessionId")
    
    if sessionId and await get_session(sessionId):
        return RedirectResponse("/dashboard", status_code=302)

    with open("static/index.html") as html:
        return HTMLResponse(content=html.read())
  
@app.get("/dashboard", response_class=HTMLResponse)
@auth_required
async def get_html(request: Request) -> HTMLResponse:
    session = await get_session(request.cookies.get("sessionId"))
    if not session:
        pass

    userId = session.get("user_id")
    user = await get_user_by_id(userId)
    if not user:
        pass

    return HTMLResponse(content=serve_content("static/dashboard.html", request.state.username))
  
@app.get("/wardrobe", response_class=HTMLResponse)
@auth_required
async def get_html(request: Request) -> HTMLResponse:
    return HTMLResponse(content=serve_content("static/wardrobe.html", request.state.username))
  
@app.get("/profile/{username}", response_class=HTMLResponse)
@auth_required
async def get_html(request: Request, username: str) -> HTMLResponse:
    if username != request.state.username:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return HTMLResponse(content=serve_content("static/profile.html", request.state.username))
  
@app.get("/login", response_class=HTMLResponse)
async def get_html(request: Request) -> HTMLResponse:
    sessionId = request.cookies.get("sessionId")
    
    if sessionId and await get_session(sessionId):
        return RedirectResponse("/dashboard", status_code=302)

    with open("static/login.html") as html:
        return HTMLResponse(content=html.read())
  
@app.get("/signup", response_class=HTMLResponse)
async def get_html(request: Request) -> HTMLResponse:
    sessionId = request.cookies.get("sessionId")
    
    if sessionId and await get_session(sessionId):
        return RedirectResponse("/dashboard", status_code=302)

    with open("static/signup.html") as html:
        return HTMLResponse(content=html.read())
  

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)