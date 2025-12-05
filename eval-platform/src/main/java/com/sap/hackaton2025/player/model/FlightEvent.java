package com.sap.hackaton2025.player.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class FlightEvent {
    public String eventType;
    public String flightNumber;
    public String flightId;
    public String aircraftType;
    public KitClasses passengers;
}