from fastapi import APIRouter, HTTPException

from src.agents.wellness.agent import WellnessAgent
from src.database.firestore_client import db

router = APIRouter(prefix="/agent", tags=["agent"])
wellness_agent = WellnessAgent()


@router.post("/{userId}/analyze")
async def analyze(userId: str):
    try:
        return wellness_agent.analyze(userId)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Gemini no retornó JSON válido: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{userId}/recommendation")
async def get_recommendation(userId: str):
    try:
        from google.cloud.firestore import FieldFilter

        docs = db.collection("recommendations").where(
            filter=FieldFilter("userId", "==", userId)
        ).stream()
        results = sorted(
            [d.to_dict() for d in docs],
            key=lambda x: x.get("generadoEn", ""),
            reverse=True,
        )
        if not results:
            return {"userId": userId, "message": "Sin recomendación disponible"}
        return results[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{userId}/recommendations")
async def get_recommendations(userId: str):
    try:
        from google.cloud.firestore import FieldFilter

        docs = db.collection("recommendations").where(
            filter=FieldFilter("userId", "==", userId)
        ).stream()
        results = sorted(
            [d.to_dict() for d in docs],
            key=lambda x: x.get("generadoEn", ""),
            reverse=True,
        )[:5]
        return {"userId": userId, "total": len(results), "recommendations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{userId}/alerts")
async def get_alerts(userId: str):
    try:
        from google.cloud.firestore import FieldFilter

        docs = db.collection("recommendations").where(
            filter=FieldFilter("userId", "==", userId)
        ).stream()
        results = sorted(
            [d.to_dict() for d in docs],
            key=lambda x: x.get("generadoEn", ""),
            reverse=True,
        )
        if not results or not results[0].get("alerta"):
            return {"userId": userId, "alerts": []}
        data = results[0]
        return {
            "userId": userId,
            "alerts": [
                {
                    "tipo": "sobreentrenamiento",
                    "mensaje": data["alerta"],
                    "fecha": data.get("generadoEn", ""),
                }
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
