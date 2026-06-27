const API_HOST = window.location.hostname;
const API_PORT = 8000;

export const API_BASE = `http://${API_HOST}:${API_PORT}`;
export const WS_URL = `ws://${API_HOST}:${API_PORT}/stream`;
