import requests
import json
from player.models import RoundResponse

class ApiService:
    API_KEY = "101f9a4d-242e-4d4a-83c5-409d58153701"
    BASE_URL = "http://127.0.0.1:8080/api/v1"
    
    def __init__(self):
        self.session_id = ""
        self.headers = {
            "API-KEY": self.API_KEY,
            "Content-Type": "application/json"
        }

    def start_session(self):
        url = f"{self.BASE_URL}/session/start"
        # POST with empty body
        resp = requests.post(url, headers=self.headers)
        
        if resp.status_code == 200:
            body = resp.text.strip()
            # Handle potential JSON response or plain string
            if body.startswith("{"):
                data = resp.json()
                self.session_id = data.get("sessionId") or data.get("id") or body
            else:
                self.session_id = body.replace('"', '')
            
            # Update headers with session ID for future requests
            self.headers["SESSION-ID"] = self.session_id
        else:
            raise Exception(f"Start Failed: {resp.text}")

    def end_session(self):
        if not self.session_id: return
        url = f"{self.BASE_URL}/session/end"
        try:
            requests.post(url, headers=self.headers)
        except Exception as e:
            print(f"Error ending session: {e}")

    def play_round(self, round_request):
        url = f"{self.BASE_URL}/play/round"
        
        payload = round_request.to_dict()
        
        # Trimitem cererea
        resp = requests.post(url, headers=self.headers, json=payload)
        
        # Verificăm dacă jocul s-a terminat
        if resp.status_code == 400 and "Session already ended" in resp.text:
            return None, None # <-- Returnăm dublu None
            
        if resp.status_code != 200:
            raise Exception(f"Server Error {resp.status_code}: {resp.text}")
            
        data = resp.json() 
        
        # Returnăm TUPLU: (Obiectul procesat, Datele brute)
        return RoundResponse(data), data

    def get_session_id(self):
        return self.session_id