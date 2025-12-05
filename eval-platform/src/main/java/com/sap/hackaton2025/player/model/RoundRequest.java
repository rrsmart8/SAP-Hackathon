package com.sap.hackaton2025.player.model;

import java.util.ArrayList;
import java.util.List;

public class RoundRequest {
    public int day;
    public int hour;
    public List<FlightLoadDto> flightLoads = new ArrayList<>();
    
    public static class FlightLoadDto {
        public String flightId;
        public KitClasses loadedKits;
        public FlightLoadDto(String id, KitClasses kits) { this.flightId = id; this.loadedKits = kits; }
    }
}