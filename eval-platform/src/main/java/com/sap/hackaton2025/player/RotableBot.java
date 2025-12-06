package com.sap.hackaton2025.player;

import com.sap.hackaton2025.player.model.*;
import com.sap.hackaton2025.player.service.*;
import java.util.Map;

public class RotableBot {

    public static void main(String[] args) {
        CsvService csvService = new CsvService();
        ApiService apiService = new ApiService();

        LogService logger = new LogService();
        
        // Loading aircraft types from CSV
        Map<String, AircraftType> aircraftMap = csvService.loadAircraftTypes();
        StrategyService strategy = new StrategyService(aircraftMap, logger);

        try {
            // Starting the game session
            apiService.startSession();
            logger.info("Session ID:" + apiService.getSessionId());

            // Game loop
            int currentDay = 0;
            int currentHour = 0;
            boolean gameRunning = true;

            while (gameRunning) { 
                RoundRequest request = new RoundRequest();
                request.day = currentDay;
                request.hour = currentHour;
                
                strategy.applyDecisionsToRequest(request);
                
                RoundResponse response = apiService.playRound(request);

                if (response == null)
                {
                    logger.info("Received null response, ending game.");
                    gameRunning = false;
                    break;
                }
                
                logger.info("--- Day " + currentDay + " : Hour " + currentHour +
                        " | Cost: " + response.totalCost +
                        " | Flights: " + response.flightUpdates.size());

                // Analyze flight events and update strategy
                strategy.analyzeEvents(response.flightUpdates);
                

                currentHour++;
                if (currentHour >= 24) {
                    currentHour = 0;
                    currentDay++;
                }

            }

            apiService.endSession();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}