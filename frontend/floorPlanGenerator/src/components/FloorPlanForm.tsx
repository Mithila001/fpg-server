import React, { useState } from "react";
import type { RoomIn, Boundary } from "../types/baseTypes";

interface FloorPlanFormProps {
  onGenerate: (boundary: Boundary, rooms: RoomIn[]) => void;
}

const FloorPlanForm: React.FC<FloorPlanFormProps> = ({ onGenerate }) => {
  const [boundary, setBoundary] = useState<Boundary>({ width: 1000, height: 800 });
  const [rooms, setRooms] = useState<RoomIn[]>([
    { width: 1000, height: 200 },
    { width: 250, height: 150 },
    { width: 200, height: 100 },
  ]);

  const handleBoundaryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBoundary({ ...boundary, [e.target.name]: Number(e.target.value) });
  };

  const handleRoomChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const newRooms = [...rooms];
    newRooms[index] = { ...newRooms[index], [e.target.name]: Number(e.target.value) };
    setRooms(newRooms);
  };

  const addRoom = () => {
    setRooms([...rooms, { width: 100, height: 100 }]);
  };

  const removeRoom = (index: number) => {
    const newRooms = rooms.filter((_, i) => i !== index);
    setRooms(newRooms);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate(boundary, rooms);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col space-y-6">
      <div className="space-y-4">
        <h3 className="text-xl font-semibold text-gray-700">Boundary Dimensions</h3>
        <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
          <label className="flex-1">
            <span className="text-sm font-medium text-gray-600">Width</span>
            <input
              type="number"
              name="width"
              value={boundary.width}
              onChange={handleBoundaryChange}
              className="mt-1 p-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring focus:ring-blue-200"
            />
          </label>
          <label className="flex-1">
            <span className="text-sm font-medium text-gray-600">Height</span>
            <input
              type="number"
              name="height"
              value={boundary.height}
              onChange={handleBoundaryChange}
              className="mt-1 p-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring focus:ring-blue-200"
            />
          </label>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-semibold text-gray-700">Rooms</h3>
        {rooms.map((room, index) => (
          <div key={index} className="p-4 border border-gray-200 rounded-md space-y-2 relative">
            <div className="flex justify-between items-center mb-2">
              <span className="text-lg font-medium">Room {index + 1}</span>
              <button
                type="button"
                onClick={() => removeRoom(index)}
                className="text-red-500 hover:text-red-700 text-sm"
              >
                Remove
              </button>
            </div>
            {/* We'll use a flex container for the inputs */}
            <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
              <label className="flex-1">
                <span className="text-sm font-medium text-gray-600">Width</span>
                <input
                  type="number"
                  name="width"
                  value={room.width}
                  onChange={(e) => handleRoomChange(index, e)}
                  className="mt-1 p-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring focus:ring-blue-200"
                />
              </label>
              <label className="flex-1">
                <span className="text-sm font-medium text-gray-600">Height</span>
                <input
                  type="number"
                  name="height"
                  value={room.height}
                  onChange={(e) => handleRoomChange(index, e)}
                  className="mt-1 p-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring focus:ring-blue-200"
                />
              </label>
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={addRoom}
          className="w-full py-2 px-4 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
        >
          Add Room
        </button>
      </div>

      <button
        type="submit"
        className="w-full py-3 px-4 bg-blue-500 text-white font-bold rounded-md hover:bg-blue-600 transition-colors"
      >
        Generate Floor Plan
      </button>
    </form>
  );
};

export default FloorPlanForm;
