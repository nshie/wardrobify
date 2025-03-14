import os
import time
import logging
import mysql.connector

from typing import Optional
from dotenv import load_dotenv
from mysql.connector import Error

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Custom exception for database connection failures"""
    pass


def get_db_connection(
    max_retries: int = 12,  # 12 retries = 1 minute total (12 * 5 seconds)
    retry_delay: int = 5,  # 5 seconds between retries
) -> mysql.connector.MySQLConnection:
    """Create database connection with retry mechanism."""
    connection: Optional[mysql.connector.MySQLConnection] = None
    attempt = 1
    last_error = None

    while attempt <= max_retries:
        try:
            connection = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=os.getenv("MYSQL_DATABASE"),
                port=int(os.getenv('MYSQL_PORT')),
                ssl_ca=os.getenv('MYSQL_SSL_CA'),
                ssl_verify_identity=True
            )

            # Test the connection
            connection.ping(reconnect=True, attempts=1, delay=0)
            logger.info("Database connection established successfully")
            return connection

        except Error as err:
            last_error = err
            logger.warning(
                f"Connection attempt {attempt}/{max_retries} failed: {err}. "
                f"Retrying in {retry_delay} seconds..."
            )

            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

            if attempt == max_retries:
                break

            time.sleep(retry_delay)
            attempt += 1

    raise DatabaseConnectionError(
        f"Failed to connect to database after {max_retries} attempts. "
        f"Last error: {last_error}"
    )

async def setup_database(initial_users: dict = None):
    connection = None
    cursor = None

    # Define table schemas
    table_schemas = {
        "users": """
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                location VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "sessions": """
            CREATE TABLE sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id INT NOT NULL,
                last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """,
        "sensors": """
            CREATE TABLE sensors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                type VARCHAR(255) NOT NULL,
                units VARCHAR(255) NOT NULL,
                address VARCHAR(255) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """,
        "clothes": """
            CREATE TABLE clothes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(255) NOT NULL,
                image_address VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """,
        "data": """
            CREATE TABLE data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                address VARCHAR(255) NOT NULL,
                type VARCHAR(255) NOT NULL,
                value FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }

    try:
        # Get database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Drop and recreate tables one by one
        for table_name in ["data", "clothes", "sensors", "sessions", "users"]:
            # Drop table if exists
            logger.info(f"Dropping table {table_name} if exists...")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            connection.commit()

        # Recreate tables one by one
        for table_name, create_query in table_schemas.items():
            try:
                # Create table
                logger.info(f"Creating table {table_name}...")
                cursor.execute(create_query)
                connection.commit()
                logger.info(f"Table {table_name} created successfully")

            except Error as e:
                logger.error(f"Error creating table {table_name}: {e}")
                raise

        # Insert initial users if provided
        if initial_users:
            try:
                insert_query = "INSERT INTO users (username, password, email, location) VALUES (%s, %s, %s, %s)"
                for username, password, email, location in initial_users:
                    cursor.execute(insert_query, (username, password, email, location))
                connection.commit()
                logger.info(f"Inserted {len(initial_users)} initial users")
            except Error as e:
                logger.error(f"Error inserting initial users: {e}")
                raise

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            logger.info("Database connection closed")


async def create_session(user_id: int, session_id: str) -> bool:
    """Create a new session in the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id) VALUES (%s, %s)", (session_id, user_id)
        )
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session from database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT *
            FROM sessions s
            WHERE s.id = %s;
            """,
            (session_id,)
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def extend_session(session_id: str) -> bool:
    """
    Extend session lifetime.

    Args:
        session_id: ID of the session to extend

    Returns:
        bool: whether the session successfully extended
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            UPDATE sessions
            SET last_access = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (session_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.exception(f"Error extending session: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def delete_session_by_id(session_id: str) -> bool:
    """Delete a session from the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def delete_session_by_user_id(user_id: str) -> bool:
    """Delete a session from the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """
    Retrieve user from database by ID.

    Args:
        user_id: ID of the user to retrieve

    Returns:
        Optional[dict]: User data if found, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_user_by_username(username: str) -> Optional[dict]:
    """Retrieve user from database by username."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def create_user(username: str, password: str, email: str, location: str) -> Optional[int]:
    """
    Create a new user in the database.
    
    Args:
        username: Username of the new user
        password: Password of the new user
        email:    Email of the new user
        location: Location of the new user

    Returns:
        Optional[int]: New user ID if successful, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, email, location) VALUES (%s, %s, %s, %s)", (username, password, email, location)
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def update_user_by_id(user_id: int, new_username: Optional[str], new_password: Optional[str], new_email: Optional[str], new_location: Optional[str]) -> bool:
    """
    Update a user in the database.
    
    Args:
        user_id: ID of the user to delete
        new_password: New password
        new_email: New email
        new_location: New Location

    Returns:
        bool: True if successful, False if failed
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
    
        if not new_username and not new_password and not new_email and not new_location:
            return True
        
        fields = []
        values = {"id": user_id}

        if new_username:
            fields.append("username = %(username)s")
            values["username"] = new_username

        if new_password:
            fields.append("password = %(password)s")
            values["password"] = new_password

        if new_email:
            fields.append("email = %(email)s")
            values["email"] = new_email

        if new_location:
            fields.append("location = %(location)s")
            values["location"] = new_location

        cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %(id)s", values)

        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def delete_user_by_id(user_id: int) -> bool:
    """
    Delete a user in the database.
    
    Args:
        user_id: ID of the user to delete

    Returns:
        bool: True if successful, False if failed
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM users WHERE id = %s", (user_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_sensor_by_id(sensor_id: str) -> Optional[dict]:
    """Retrieve sensor from database by ID."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM sensors WHERE id = %s",
            (sensor_id,)
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_sensors_by_user_id(user_id: int) -> list[int]:
    """
    Get all sensors belonging to a user.
    
    Args:
        user_id:    ID of the user

    Returns:
        list[int]: List of all sensors belonging to the user
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM sensors WHERE user_id = %s",
            (user_id,)
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def add_sensor(user_id: int, type: str, units: str, address: str) -> Optional[int]:
    """
    Add a sensor to the database.
    
    Args:
        user_id:    ID of the user to add the sensor to
        type:       Type of sensor
        units:      Units of the sensor readings
        address:    Address of the sensor

    Returns:
        Optional[int]: New sensor ID if successful, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO sensors (user_id, type, units, address) VALUES (%s, %s, %s, %s)",
            (user_id, type, units, address)
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def update_sensor(sensor_id: int, new_type: Optional[str] = None, new_units: Optional[str] = None, new_address: Optional[str] = None) -> bool:
    """
    Add a sensor to the database.
    
    Args:
        sensor_id:      ID of the sensor to update
        new_type:       New type of sensor
        new_units:      New units of the sensor readings
        new_address:    New Address of the sensor

    Returns:
        True if successful, False otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if not new_type and not new_units and not new_address:
            return True
        
        fields = []
        values = {"id": sensor_id}

        if new_type:
            fields.append("type = %(type)s")
            values["type"] = new_type

        if new_units:
            fields.append("units = %(units)s")
            values["units"] = new_units

        if new_address:
            fields.append("address = %(address)s")
            values["address"] = new_address

        cursor.execute(
            f"UPDATE sensors SET {', '.join(fields)} WHERE id = %(id)s", values
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def delete_sensor(sensor_id: int) -> bool:
    """
    Delete a sensor from the database.
    
    Args:
        sensor_id:  ID of the sensor to delete

    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM sensors WHERE id = %s",
            (sensor_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_clothes_by_id(clothes_id: int) -> Optional[dict]:
    """Retrieve article of clothing by ID"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM clothes WHERE id = %s",
            (clothes_id,)
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_clothes_by_user_id(user_id: int) -> list[dict]:
    """
    Get all clothing items belonging to a user.
    
    Args:
        user_id:    ID of the user

    Returns:
        list[int]: List of all clothing items belonging to the user
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM clothes WHERE user_id = %s",
            (user_id,)
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def add_clothes(user_id: int, name: str, type: str, image_address: str) -> Optional[int]:
    """
    Add an article of clothing to the database.
    
    Args:
        user_id:        ID of the user to add the clothing to
        name:           Name of the article of clothing
        type:           Type of clothing
        image_address:  Image address of the article of clothing

    Returns:
        Optional[int]: New clothing ID if successful, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO clothes (user_id, name, type, image_address) VALUES (%s, %s, %s, %s)",
            (user_id, name, type, image_address)
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def update_clothes(clothes_id: int, new_name: Optional[str], new_type: Optional[str], new_image_address: Optional[str]) -> bool:
    """
    Update an article of clothing in the database.
    
    Args:
        clothes_id:     ID of the article of clothing to update
        name:           Name of the article of clothing
        type:           Type of clothing
        image_address:  Image address of the article of clothing

    Returns:
        Optional[int]: New clothing ID if successful, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if not new_name and not new_type and not new_image_address:
            return True
        
        fields = []
        values = {"id": clothes_id}

        if new_name:
            fields.append("name = %(name)s")
            values["name"] = new_name

        if new_type:
            fields.append("type = %(type)s")
            values["type"] = new_type

        if new_image_address:
            fields.append("image_address = %(image_address)s")
            values["image_address"] = new_image_address

        cursor.execute(
            f"UPDATE clothes SET {', '.join(fields)} WHERE id = %(id)s", values
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def delete_clothes(clothes_id: int) -> True:
    """
    Delete an article of clothing from the database.
    
    Args:
        clothes_id:  The ID of the clothing to delete

    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM clothes WHERE id = %s",
            (clothes_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def add_data(value: float, type: str, address: str) -> Optional[int]:
    """
    Add sensor data to the database.
    
    Args:
        value:      Value of sensor reading
        type:       Type of sensor
        address:    Address of the sensor

    Returns:
        Optional[int]: New data ID if successful, None otherwise
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO data (value, type, address) VALUES (%s, %s, %s)",
            (value, type, address)
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_data_by_sensor_id(sensor_id: int, limit: int = 20) -> list[dict]:
    """
    Get data belonging to a sensor.
    
    Args:
        sensor_id:    ID of the sensor

    Returns:
        list[int]: List of all data belonging to that sensor
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sensors WHERE id = %s", (sensor_id,))
        sensor = cursor.fetchone()
        sensor_address = sensor.get('address')

        cursor.execute(
            '''
            SELECT * FROM data
            WHERE address = %s
            ORDER BY timestamp DESC
            LIMIT %s;
            ''',
            (sensor_address, limit)
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


async def get_recent_data(sensor_id: int) -> Optional[dict]:
    """
    Get most recent data belonging to a sensor.
    
    Args:
        sensor_id:    ID of the sensor

    Returns:
        Optional[dict]: Most recent data belonging to that sensor or None
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT d.* FROM data d
            JOIN sensors s ON s.address = d.address AND s.type = d.type
            WHERE s.id = %s 
            ORDER BY d.timestamp DESC
            LIMIT 1;
            ''', (sensor_id,)
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()