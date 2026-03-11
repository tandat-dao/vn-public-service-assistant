import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (process.env.NODE_ENV === "development") {
      console.error("[API Error]", error.response?.status, error.response?.data);
    }
    return Promise.reject(error);
  }
);
