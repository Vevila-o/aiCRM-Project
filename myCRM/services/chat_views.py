import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from myCRM.models import AiSuggection

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@csrf_exempt
def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_msg = (data.get("message") or "").strip()
        categoryID = int(data.get("categoryID") or 0)
    except Exception as e:
        return JsonResponse({"error": f"invalid json: {e}"}, status=400)

    if not user_msg:
        return JsonResponse({"error": "message is required"}, status=400)
    if not categoryID:
        return JsonResponse({"error": "categoryID is required"}, status=400)

    messages = [
        {"role": "system", "content": "你是一位中文行銷顧問，會依顧客類別提供具體建議。"},
        {"role": "user", "content": f"顧客類別ID：{categoryID}。\n問題：{user_msg}"},
    ]

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        reply = completion.choices[0].message.content

        AiSuggection.objects.create(
            categoryID=categoryID,
            content=reply,
        )

    except Exception as e:
        return JsonResponse({"error": f"server error: {e}"}, status=500)

    return JsonResponse({"reply": reply})
