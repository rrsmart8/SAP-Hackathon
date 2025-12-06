import os
from player.models import AircraftType

class CsvService:
    DATA_FOLDER = "src/main/resources/liquibase/data/"

    def load_aircraft_types(self):
        aircraft_map = {}
        file_path = os.path.join(self.DATA_FOLDER, "aircraft_types.csv")
        
        if not os.path.exists(file_path):
            print(f"!!! CRITICAL: CSV not found at {file_path}")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                header = f.readline() # Skip header
                for line in f:
                    line = line.strip()
                    if not line: continue
                    
                    # Split după punct și virgulă
                    cols = line.split(";")
                    
                    if len(cols) < 11:
                        print(f"Skipping invalid line: {line}")
                        continue
                    
                    type_code = cols[1].strip() # Curățăm spațiile
                    
                    try:
                        cap_f = int(cols[7])
                        cap_b = int(cols[8])
                        cap_p = int(cols[9])
                        cap_e = int(cols[10])
                        
                        aircraft_map[type_code] = AircraftType(type_code, cap_f, cap_b, cap_p, cap_e)
                    except ValueError:
                        print(f"Error parsing numbers for {type_code}")

            print(f"   -> [CSV] Loaded {len(aircraft_map)} aircraft types.")
            print(f"   -> [CSV] Available types: {list(aircraft_map.keys())}")
            return aircraft_map
            
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return {}
            
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return {}