package com.sap.hackaton2025.player.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class KitClasses {
    @JsonProperty("first") public int firstClass;
    @JsonProperty("business") public int business;
    @JsonProperty("premiumEconomy") public int premiumEconomy;
    @JsonProperty("economy") public int economy;

    public KitClasses() {}

    public KitClasses(int f, int b, int p, int e) {
        this.firstClass = f; this.business = b; this.premiumEconomy = p; this.economy = e;
    }

    @Override
    public String toString() {
        return String.format("[First:%d Business:%d Premium:%d Economy:%d]", firstClass, business, premiumEconomy, economy);
    }
}