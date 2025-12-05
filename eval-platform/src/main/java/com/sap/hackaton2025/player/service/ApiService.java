package com.sap.hackaton2025.player.service;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sap.hackaton2025.player.model.RoundRequest;
import com.sap.hackaton2025.player.model.RoundResponse;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class ApiService {
    private static final String API_KEY = "ee3dd8b7-9e63-4054-b976-cfa35cafb3c2"; 
    private static final String BASE_URL = "http://127.0.0.1:8080/api/v1";
    
    private final HttpClient client = HttpClient.newHttpClient();
    private final ObjectMapper mapper = new ObjectMapper();
    private String sessionId = "";

    public void startSession() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + "/session/start"))
                .header("API-KEY", API_KEY)
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        HttpResponse<String> resp = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() == 200) {
            String body = resp.body().trim();
            if (body.startsWith("{")) {
                JsonNode node = mapper.readTree(body);
                if (node.has("sessionId")) sessionId = node.get("sessionId").asText();
                else if (node.has("id")) sessionId = node.get("id").asText();
                else sessionId = body;
            } else {
                sessionId = body.replace("\"", "");
            }
        } else {
            throw new RuntimeException("Start Failed: " + resp.body());
        }
    }

    public void endSession() {
        try {
            if (sessionId.isEmpty()) return;
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(BASE_URL + "/session/end"))
                    .header("API-KEY", API_KEY)
                    .header("SESSION-ID", sessionId)
                    .POST(HttpRequest.BodyPublishers.noBody())
                    .build();
            client.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (Exception e) {
            System.err.println("Error closing session: " + e.getMessage());
        }
    }

    public RoundResponse playRound(RoundRequest payload) throws Exception {
        String jsonBody = mapper.writeValueAsString(payload);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + "/play/round"))
                .header("API-KEY", API_KEY)
                .header("SESSION-ID", sessionId)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> resp = client.send(request, HttpResponse.BodyHandlers.ofString());
        
        if (resp.statusCode() == 400 && resp.body().contains("Session already ended")) {
            return null; 
        }
        if (resp.statusCode() != 200) {
            throw new RuntimeException("Server Error " + resp.statusCode() + ": " + resp.body());
        }
        return mapper.readValue(resp.body(), RoundResponse.class);
    }
    
    public String getSessionId() { return sessionId; }
}