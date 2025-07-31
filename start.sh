#!/bin/bash
# Lancement du serveur FastAPI pour Render
uvicorn webhook:app --host 0.0.0.0 --port $PORT
