-- CreateTable
CREATE TABLE "Colony" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'ALIVE',
    "launchDate" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sol" INTEGER NOT NULL DEFAULT 0,
    "solarLongitude" REAL NOT NULL DEFAULT 0.0,
    "latitude" REAL NOT NULL DEFAULT -4.5,
    "longitude" REAL NOT NULL DEFAULT 137.4,
    "locationName" TEXT NOT NULL DEFAULT 'Jezero Crater',
    "panelAreaM2" REAL NOT NULL DEFAULT 400,
    "insulationR" REAL NOT NULL DEFAULT 12,
    "heaterPowerW" REAL NOT NULL DEFAULT 8000,
    "groundDepthM" REAL NOT NULL DEFAULT 0,
    "crewSize" INTEGER NOT NULL DEFAULT 4,
    "interiorTempK" REAL NOT NULL DEFAULT 293.0,
    "storedEnergyKwh" REAL NOT NULL DEFAULT 500.0,
    "panelDustFactor" REAL NOT NULL DEFAULT 1.0,
    "waterReservesL" REAL NOT NULL DEFAULT 200.0,
    "foodReservesKg" REAL NOT NULL DEFAULT 120.0,
    "harvestTotalKg" REAL NOT NULL DEFAULT 0.0,
    "solsSurvived" INTEGER NOT NULL DEFAULT 0,
    "totalPowerKwh" REAL NOT NULL DEFAULT 0.0,
    "totalHeatingKwh" REAL NOT NULL DEFAULT 0.0,
    "dustDevils" INTEGER NOT NULL DEFAULT 0,
    "stormsSurvived" INTEGER NOT NULL DEFAULT 0,
    "meteorites" INTEGER NOT NULL DEFAULT 0,
    "minTempK" REAL NOT NULL DEFAULT 293.0,
    "maxTempK" REAL NOT NULL DEFAULT 293.0,
    "harvests" INTEGER NOT NULL DEFAULT 0,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Event" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "colonyId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "severity" REAL NOT NULL DEFAULT 0.0,
    "startSol" INTEGER NOT NULL,
    "endSol" INTEGER NOT NULL,
    "description" TEXT NOT NULL,
    CONSTRAINT "Event_colonyId_fkey" FOREIGN KEY ("colonyId") REFERENCES "Colony" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Log" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "colonyId" TEXT NOT NULL,
    "sol" INTEGER NOT NULL,
    "ls" REAL NOT NULL,
    "intC" REAL NOT NULL,
    "extC" REAL NOT NULL,
    "solarKwh" REAL NOT NULL,
    "heatKwh" REAL NOT NULL,
    "storedKwh" REAL NOT NULL,
    "dust" REAL NOT NULL,
    "foodKg" REAL NOT NULL,
    "events" TEXT NOT NULL,
    "storm" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "Log_colonyId_fkey" FOREIGN KEY ("colonyId") REFERENCES "Colony" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
