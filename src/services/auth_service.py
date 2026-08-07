from datetime import datetime

from firebase_admin import auth

from src.database.firestore_client import db


def register_user(email: str, password: str, nombre: str, peso: float, edad: int, nivel: str) -> dict:
    user = auth.create_user(email=email, password=password, display_name=nombre)
    profile = {
        "uid": user.uid,
        "email": email,
        "nombre": nombre,
        "peso": peso,
        "edad": edad,
        "nivel": nivel,
        "createdAt": datetime.utcnow().isoformat(),
    }
    db.collection("users").document(user.uid).set(profile)
    return {"uid": user.uid, "email": user.email, "nombre": nombre, "message": "Usuario registrado exitosamente"}


def get_user(uid: str) -> dict:
    user = auth.get_user(uid)
    doc = db.collection("users").document(uid).get()
    profile = doc.to_dict() if doc.exists else {}
    return {
        "uid": user.uid,
        "email": user.email,
        "nombre": profile.get("nombre", user.display_name),
        "peso": profile.get("peso"),
        "edad": profile.get("edad"),
        "nivel": profile.get("nivel"),
    }


def update_user(uid: str, updates: dict) -> dict:
    if not updates:
        raise ValueError("No hay datos para actualizar")
    if "nombre" in updates:
        auth.update_user(uid, display_name=updates["nombre"])
    updates["updatedAt"] = datetime.utcnow().isoformat()
    db.collection("users").document(uid).set(updates, merge=True)
    return {"uid": uid, "message": "Perfil actualizado exitosamente"}
