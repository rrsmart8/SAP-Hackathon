package com.sap.hackaton2025.player.service;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class LogService {

    private static final String LOG_FILE = "bot_history.log";
    private PrintWriter writer;
    private final DateTimeFormatter dtf = DateTimeFormatter.ofPattern("HH:mm:ss");

    public LogService() {
        try {
            FileWriter fw = new FileWriter(LOG_FILE, true); 
            writer = new PrintWriter(fw, true); 
            info(">>> SESIUNE NOUA START <<<");
            System.out.println("Log initialised here: " + LOG_FILE);
        } catch (IOException e) {
            System.err.println("Nu pot crea fisierul de log: " + e.getMessage());
        }
    }

    public void info(String message) {
        String timestamp = "[" + dtf.format(LocalDateTime.now()) + "] ";
        String fullMessage = timestamp + message;

        if (writer != null) {
            writer.println(fullMessage);
        }
    }

    public void close() {
        if (writer != null) {
            writer.close();
        }
    }
}