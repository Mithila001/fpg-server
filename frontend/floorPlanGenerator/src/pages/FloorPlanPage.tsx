import React, { useState } from "react";
import { Stage, Layer, Rect, Text } from "react-konva";
import FloorPlanForm from "../components/FloorPlanForm";
import { generateLayout } from "../services/floorPlanService";
import type { RoomOut } from "../types/baseTypes";

// Helper function to generate a random color
const getRandomColor = () => {
  const letters = "0123456789ABCDEF";
  let color = "#";
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
};

const FloorPlanPage: React.FC = () => {
  const [boundary, setBoundary] = useState({ width: 1000, height: 800 });
  const [placedRooms, setPlacedRooms] = useState<RoomOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (boundaryData: any, roomsData: any) => {
    setError(null);
    try {
      const result = await generateLayout({ boundary: boundaryData, rooms: roomsData });
      setBoundary(boundaryData);
      setPlacedRooms(result);
    } catch (err: any) {
      setError(err.message);
      setPlacedRooms([]);
    }
  };

  return (
    <div className="flex flex-col items-center p-8 bg-gray-100 min-h-screen">
      <h2 className="text-3xl font-bold mb-6 text-gray-800">Floor Plan Generator</h2>

      {/* Main content container with a row-based layout on large screens */}
      <div className="flex flex-col lg:flex-row w-full max-w-6xl gap-8">
        {/* Form container */}
        <div className="bg-white p-6 rounded-lg shadow-lg w-full lg:w-1/3">
          <FloorPlanForm onGenerate={handleGenerate} />
          {error && <p className="text-red-500 mt-4 text-center">{error}</p>}
        </div>

        {/* Visualization container */}
        <div className="bg-white p-4 rounded-lg shadow-lg w-full lg:w-2/3 flex items-center justify-center overflow-auto">
          {/* This div is the container for the Konva Stage */}
          <Stage width={boundary.width} height={boundary.height} className="border border-gray-300">
            <Layer>
              {/* The outer boundary rectangle with a clear border */}
              <Rect
                x={0}
                y={0}
                width={boundary.width}
                height={boundary.height}
                stroke="black"
                strokeWidth={2}
                listening={false}
              />

              {/* The rooms with random colors and labels */}
              {placedRooms.map((room) => (
                <React.Fragment key={room.id}>
                  <Rect
                    x={room.x}
                    y={room.y}
                    width={room.width}
                    height={room.height}
                    fill={getRandomColor()}
                    stroke="black"
                    strokeWidth={1}
                  />
                  <Text
                    x={room.x + 5}
                    y={room.y + 5}
                    text={`Room ${room.id}\n(${room.width}x${room.height})`}
                    fontSize={14}
                    fill="white"
                  />
                </React.Fragment>
              ))}
            </Layer>
          </Stage>
        </div>
      </div>
    </div>
  );
};

export default FloorPlanPage;
