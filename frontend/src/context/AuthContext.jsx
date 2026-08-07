import { createContext, useContext, useEffect, useState } from 'react'
import { initializeApp } from 'firebase/app'
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup
} from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

const app = initializeApp(firebaseConfig)
const auth = getAuth(app)

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('darkMode') === 'true')

  const toggleDarkMode = () => {
    setDarkMode(prev => {
      localStorage.setItem('darkMode', !prev)
      return !prev
    })
  }
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser)
      setLoading(false)
    })
    return unsubscribe
  }, [])

  const login = (email, password) =>
    signInWithEmailAndPassword(auth, email, password)

  const register = (email, password) =>
    createUserWithEmailAndPassword(auth, email, password)

  const logout = () => signOut(auth)

  const loginWithGoogle = async () => {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    return result
  }
  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, loginWithGoogle, darkMode, toggleDarkMode }}>
      {!loading && children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)