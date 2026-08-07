import axios from 'axios'
import { getAuth } from 'firebase/auth'

const AUTH_URL = import.meta.env.VITE_AUTH_URL
const SESSIONS_URL = import.meta.env.VITE_SESSIONS_URL
const METRICS_URL = import.meta.env.VITE_METRICS_URL
const AGENT_URL = import.meta.env.VITE_AGENT_URL

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
// AGENT
export const analyzeWithAgent = async (userId) => {
  const headers = await authHeader()
  return axios.post(`${AGENT_URL}/agent/${userId}/analyze`, {}, { headers })
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

export const getUser = async (uid) => {
  const headers = await authHeader()
  return axios.get(`${AUTH_URL}/auth/user/${uid}`, { headers })
}
// PROFILE
export const updateProfile = async (uid, data) => {
  const headers = await authHeader()
  return axios.put(`${AUTH_URL}/auth/user/${uid}`, data, { headers })
}