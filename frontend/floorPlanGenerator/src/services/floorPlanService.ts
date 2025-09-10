import client from "../api/client"; // Import the centralized client
import type { RoomIn, Boundary, RoomOut, LayoutRequest } from "../types/baseTypes";
import axios from "axios";

export const generateLayout = async (request: LayoutRequest): Promise<RoomOut[]> => {
  try {
    const response = await client.post<RoomOut[]>("/layout/generate", request);
    return response.data;
  } catch (error) {
    // Use the imported axios to check the error type
    if (axios.isAxiosError(error) && error.response) {
      console.error("Error generating layout:", error.response.data);
      throw new Error(error.response.data.detail || "Could not generate layout.");
    }
    throw new Error("An unexpected error occurred.");
  }
};
