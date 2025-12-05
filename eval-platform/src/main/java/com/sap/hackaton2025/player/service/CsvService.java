package com.sap.hackaton2025.player.service;

import com.sap.hackaton2025.player.model.AircraftType;
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.HashMap;
import java.util.Map;

public class CsvService {

    private static final String DATA_FOLDER = "src/main/resources/liquibase/data/";

    public Map<String, AircraftType> loadAircraftTypes() 
    {
        Map<String, AircraftType> map = new HashMap<>();

        try (BufferedReader br = new BufferedReader(new FileReader(DATA_FOLDER + "aircraft_types.csv")))
         {
            br.readLine(); 
            String line;

            while ((line = br.readLine()) != null) 
                {
                String[] cols = line.split(";");
                AircraftType ac = new AircraftType();
                
                ac.typeCode = cols[1];
                ac.firstClassKitsCapacity = parseInt(cols[7]);
                ac.businessKitsCapacity = parseInt(cols[8]);
                ac.premiumEconomyKitsCapacity = parseInt(cols[9]);
                ac.economyKitsCapacity = parseInt(cols[10]);
                
                map.put(ac.typeCode, ac);
            }
        } catch (Exception e) {
            System.err.println("Eroare incarcare CSV: " + e.getMessage());
        }
        return map;
    }
    private int parseInt(String val) {
        try { return Integer.parseInt(val); } catch (Exception e) { return 0; }
    }
}