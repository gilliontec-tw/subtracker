# SQL Server setup — run the following in SQL Server Management Studio before use:
#
# CREATE DATABASE saas_tracker;
# GO
# USE saas_tracker;
# GO
# CREATE TABLE saas_subscriptions (
#     id INT IDENTITY(1,1) PRIMARY KEY,
#     service_name NVARCHAR(200) NOT NULL,
#     login_account NVARCHAR(200) NOT NULL,
#     expiry_date DATE NOT NULL,
#     responsible_person_email NVARCHAR(200) NOT NULL,
#     notification_days INT NOT NULL,
#     is_active BIT NOT NULL CONSTRAINT DF_is_active DEFAULT 1,
#     created_at DATETIME2 NOT NULL CONSTRAINT DF_created_at DEFAULT GETDATE(),
#     updated_at DATETIME2 NULL
# );
# GO

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

_connection_string = os.environ["DB_CONNECTION_STRING"]
engine = create_engine(_connection_string, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
