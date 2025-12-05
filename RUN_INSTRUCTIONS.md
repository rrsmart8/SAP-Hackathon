# Flight Rotables Optimization Bot - Quick Start

## Prerequisites

  * **Java 25** installed.
  * **Maven** installed.
  * **Two Terminal windows** (or Tabs) open.

-----

## Step 1: Configuration (Do this first\!)

Before running anything, ensure the **API KEY** is correct for our team.

1.  Open file: `src/main/java/com/sap/hackaton2025/player/service/ApiService.java`
2.  Find line: `private static final String API_KEY = "...";`
3.  **Update it** with the key from `teams.csv` if it's not already there.

-----

## Step 2: Launch the Game Server (Terminal 1)

This terminal runs the "World" simulation. **Keep this open and running at all times.**

1.  Navigate to the project root (`eval-platform`).
2.  Run:
    ```bash
    mvn spring-boot:run -Dspring-boot.run.profiles=local
    ```
3.  Wait until you see: `Started Application in X seconds`.

-----

## Step 3: Run Our Bot (Terminal 2)

This terminal runs our logic. It connects to Terminal 1.

1.  Navigate to the project root (`eval-platform`).
2.  Run the Player Bot:
    ```bash
    mvn compile exec:java -Dexec.mainClass="com.sap.hackaton2025.player.RotableBot"
    ```

-----

## Where to Write Code?

We have modularized the code to keep it safe from the Server code. **Only touch files in the `player` package.**

  * **Logic & Strategy:** `src/main/java/com/sap/hackaton2025/player/service/StrategyService.java`
      * *Edit this file* to improve the algorithm (Tankering, Purchasing, etc.).
  * **API Calls:** `src/main/java/com/sap/hackaton2025/player/service/ApiService.java`
      * *Edit this* if you need to add new endpoints (like purchasing orders).
  * **Data Models:** `src/main/java/com/sap/hackaton2025/player/model/`
      * DTOs for JSON mapping.

* **DO NOT TOUCH:**

  * Anything outside the `player` folder (e.g., `FlightServiceImpl.java`, `Repository` files). Those are server internals and will break our bot.

-----

## Troubleshooting

### Error: `java.net.ConnectException`

  * **Cause:** The Server (Terminal 1) is not running or is still starting up.
  * **Fix:** Check Terminal 1. Ensure `mvn spring-boot:run` is active and finished loading.

### Error: `FileNotFoundException ... aircraft_types.csv`

  * **Cause:** The bot can't find the CSV data files.
  * **Fix:** Check `CsvService.java`. The `DATA_FOLDER` path should point to: `src/main/resources/liquibase/data/`.

### Error: `400 Bad Request (Session already ended)`

  * **Cause:** We successfully finished the 30-day simulation\!
  * **Fix:** Restart the Server in Terminal 1 (Ctrl+C, then run command again) to reset the world for a new run.