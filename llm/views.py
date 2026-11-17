import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Create your views here.

def chatbot_view(request):
    """Vista principal del chatbot"""
    return render(request, 'llm/chatbot.html')

@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """API endpoint para procesar mensajes del chatbot"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        if not user_message:
            return JsonResponse({'error': 'No se proporcionó ningún mensaje'}, status=400)
        
        # Inicializar cliente de Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Crear la conversación con el LLM
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=1,
            max_completion_tokens=8192,
            top_p=1,
            reasoning_effort="medium",
            stream=False,
            stop=None
        )
        
        # Extraer la respuesta
        response_message = completion.choices[0].message.content
        
        return JsonResponse({
            'response': response_message,
            'status': 'success'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)