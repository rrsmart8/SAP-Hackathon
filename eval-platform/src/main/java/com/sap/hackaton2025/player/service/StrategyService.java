package com.sap.hackaton2025.player.service;

import com.sap.hackaton2025.player.model.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class StrategyService {
    
    private final Map<String, AircraftType> aircraftMap;
    private final List<RoundRequest.FlightLoadDto> pendingLoads = new ArrayList<>();

    private final LogService logger; 

    public StrategyService(Map<String, AircraftType> aircraftMap, LogService logger) {
        this.aircraftMap = aircraftMap;
        this.logger = logger;
    }

    public void analyzeEvents(List<FlightEvent> events) {
        for (FlightEvent event : events) {
            if ("CHECKED_IN".equals(event.eventType)) {
                calculateLoadForFlight(event);
            }
        }
    }
    
    public void applyDecisionsToRequest(RoundRequest request) {
        request.flightLoads.addAll(pendingLoads);        
        pendingLoads.clear();
    }

    private void calculateLoadForFlight(FlightEvent event) {
        AircraftType type = aircraftMap.get(event.aircraftType);
        if (type == null) return;

        // Load exactly the number of passengers checked in, capped by aircraft capacity
        int loadE = Math.min(event.passengers.economy, type.economyKitsCapacity);
        int loadB = Math.min(event.passengers.business, type.businessKitsCapacity);
        int loadF = Math.min(event.passengers.firstClass, type.firstClassKitsCapacity);
        int loadP = Math.min(event.passengers.premiumEconomy, type.premiumEconomyKitsCapacity);

        // Create a ProcessBuilder to call a python script that will call a print

        ProcessBuilder pb = new ProcessBuilder("python3", "scripts/load.py",
                event.flightNumber,
                String.valueOf(loadF),
                String.valueOf(loadB),
                String.valueOf(loadP),
                String.valueOf(loadE)
        );

        pb.inheritIO();

        try {
            Process process = pb.start();
            process.waitFor();
        } catch (Exception e) {
            logger.info("Eroare la apelarea scriptului de logare a incarcarii: " + e.getMessage());
        }

        KitClasses load = new KitClasses(loadF, loadB, loadP, loadE);
        
        logger.info("   -> [CHECK-IN] Zbor " + event.flightNumber + " (" + event.flightId + "): " + load.toString());
        pendingLoads.add(new RoundRequest.FlightLoadDto(event.flightId, load));
    }
}