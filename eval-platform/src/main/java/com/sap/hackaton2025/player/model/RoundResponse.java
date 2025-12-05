package com.sap.hackaton2025.player.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class RoundResponse {
    public int day;
    public int hour;
    public double totalCost;
    public List<FlightEvent> flightUpdates;
}