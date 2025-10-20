import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

class DatabaseService:
    """
    DatabaseService manages a MongoDB connection pool for efficient database access.

    Features:
    - Uses a connection pool to improve performance.
    - Ensures only one database connection is shared across the app.
    - Supports environment variables for configuration.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern: Ensures only one instance of DatabaseService exists."""
        if not cls._instance:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes MongoDB connection with connection pooling."""
        self.mongo_connection_string = os.getenv("COSMOS_MONGO_STRING")
        self.database_name = os.getenv("DB_NAME")

        if not self.mongo_connection_string or not self.database_name:
            raise ValueError("MongoDB connection string and database name must be set.")

        self.client = pymongo.MongoClient(
            self.mongo_connection_string,
            maxPoolSize=20,  # Maximum number of connections in the pool
            minPoolSize=5,   # Minimum number of idle connections
            serverSelectionTimeoutMS=5000  # Timeout if unable to connect
        )

        self.db = self.client[self.database_name]
        print("MongoDB Connection Pool Initialized")

    def get_db(self):
        """Returns the database instance."""
        return self.db

    def close_connection(self):
        """Closes the MongoDB client connection."""
        if self.client:
            self.client.close()
            print("MongoDB Connection Closed")

    def get_mongo_connection_string(self):
        """
        Get Mongo Connection String.

        Returns:
            str: Mongo Connection String.
        """
        return self.mongo_connection_string

    def get_database_name(self):
        """
        Get Mongo Database Name.

        Returns:
            str: Mongo Database Name.
        """
        return self.database_name

database_service = DatabaseService()
