import axios from 'axios'
import { getAuth } from 'firebase/auth'

const AUTH_URL = import.meta.env.VITE_AUTH_URL
const SESSIONS_URL = import.meta.env.VITE_SESSIONS_URL
const METRICS_URL = import.meta.env.VITE_METRICS_URL
const AGENT_URL = import.meta.env.VITE_AGENT_URL

// El orquestador vive en el mismo backend que el agente. Se deja una variable
// propia por si algun dia se despliegan por separado, con AGENT_URL como valor
// por defecto para no romper los .env existentes.
const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || AGENT_URL

const authHeader = async () => {
  const user = getAuth().currentUser
  if (!user) return {}
  const token = await user.getIdToken()
  return { Authorization: `Bearer ${token}` }
}

// AUTH
export const registerUser = (data) =>
  axios.post(`${AUTH_URL}/auth/register`, data)

// SESSIONS
export const getSessions = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${SESSIONS_URL}/sessions/${userId}`, { headers })
}

export const createSession = async (data) => {
  const headers = await authHeader()
  return axios.post(`${SESSIONS_URL}/sessions`, data, { headers })
}

export const updateSession = async (userId, id, data) => {
  const headers = await authHeader()
  return axios.put(`${SESSIONS_URL}/sessions/${userId}/${id}`, data, { headers })
}

export const deleteSession = async (userId, id) => {
  const headers = await authHeader()
  return axios.delete(`${SESSIONS_URL}/sessions/${userId}/${id}`, { headers })
}

// GOALS
export const getGoals = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${SESSIONS_URL}/goals/${userId}`, { headers })
}

export const createGoal = async (data) => {
  const headers = await authHeader()
  return axios.post(`${SESSIONS_URL}/goals`, data, { headers })
}

export const updateGoal = async (userId, goalId, data) => {
  const headers = await authHeader()
  return axios.put(`${SESSIONS_URL}/goals/${userId}/${goalId}`, data, { headers })
}

export const deleteGoal = async (userId, goalId) => {
  const headers = await authHeader()
  return axios.delete(`${SESSIONS_URL}/goals/${userId}/${goalId}`, { headers })
}

// METRICS
export const getWeeklyMetrics = async (userId, offset = 0) => {
  const headers = await authHeader()
  return axios.get(`${METRICS_URL}/metrics/${userId}/weekly?offset=${offset}`, { headers })
}

export const getGoalProgress = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${METRICS_URL}/metrics/${userId}/goal-progress`, { headers })
}

export const getWeeklyChart = async (userId, semanas = 8) => {
  const headers = await authHeader()
  return axios.get(`${METRICS_URL}/metrics/${userId}/weekly-chart?semanas=${semanas}`, { headers })
}

export const getSummary = async (userId, semanas = 4) => {
  const headers = await authHeader()
  return axios.get(`${METRICS_URL}/metrics/${userId}/summary?semanas=${semanas}`, { headers })
}

// AGENT — recomendacion de un turno
//
// El parametro 'mode' existe en el backend desde el Sprint 1 y selecciona la
// arquitectura con la que se genera la recomendacion: 'legacy' usa un prompt
// estatico con el conocimiento embebido en el codigo, 'rag' recupera de la
// knowledge base curada y fundamenta la respuesta. Hasta ahora el frontend
// nunca lo enviaba, asi que el modo dual solo se podia ver con curl.
export const analyzeWithAgent = async (userId, mode = 'rag') => {
  const headers = await authHeader()
  return axios.post(`${AGENT_URL}/agent/${userId}/analyze?mode=${mode}`, {}, { headers })
}

// Ejecuta los dos modos sobre el mismo estado del corredor y devuelve ambas
// respuestas con sus latencias y fuentes. No persiste nada: es una operacion
// de demostracion.
export const compareAgentModes = async (userId) => {
  const headers = await authHeader()
  return axios.post(`${AGENT_URL}/agent/${userId}/compare`, {}, { headers })
}

export const getRecommendation = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${AGENT_URL}/agent/${userId}/recommendation`, { headers })
}

export const getRecommendations = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${AGENT_URL}/agent/${userId}/recommendations`, { headers })
}

export const getAlerts = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${AGENT_URL}/agent/${userId}/alerts`, { headers })
}

// ORCHESTRATOR — sistema multiagente
//
// Devuelve la respuesta junto con la traza completa: intencion detectada,
// agentes a los que se delego y por que, que se le pidio exactamente a cada
// uno, que consulto y cuanto tardo cada paso.
export const chatWithOrchestrator = async (userId, mensaje) => {
  const headers = await authHeader()
  return axios.post(
    `${ORCHESTRATOR_URL}/orchestrator/${userId}/chat`,
    { mensaje },
    { headers }
  )
}

// Turnos persistidos de la conversacion. La memoria del agente vive en
// Firestore y sobrevive a recargas, asi que la pantalla debe poder
// reconstruir lo que el agente si recuerda.
export const getChatHistory = async (userId) => {
  const headers = await authHeader()
  return axios.get(`${ORCHESTRATOR_URL}/orchestrator/${userId}/history`, { headers })
}

export const clearChatHistory = async (userId) => {
  const headers = await authHeader()
  return axios.delete(`${ORCHESTRATOR_URL}/orchestrator/${userId}/history`, { headers })
}

// USER
export const getUser = async (uid) => {
  const headers = await authHeader()
  return axios.get(`${AUTH_URL}/auth/user/${uid}`, { headers })
}

// PROFILE
export const updateProfile = async (uid, data) => {
  const headers = await authHeader()
  return axios.put(`${AUTH_URL}/auth/user/${uid}`, data, { headers })
}
