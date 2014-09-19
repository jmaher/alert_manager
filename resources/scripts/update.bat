
CALL curl -X POST http://localhost:8159/shutdown
CALL git pull origin integrate
START resources\scripts\server.bat
