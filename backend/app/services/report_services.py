import httpx
from typing import Optional
from app.config import settings

def generate_template_report(
    bone: Optional[str], 
    location: Optional[str], 
    fracture_type: Optional[str], 
    severity: Optional[str]
) -> str:
    if bone is None or fracture_type is None:
        return (
            "Radiographic evaluation demonstrates no acute osseous fracture, dislocation, or focal cortical disruption. "
            "Bone alignment, joint congruity, and mineralization appear within normal radiological limits. "
            "No significant soft tissue swelling or periosteal reaction identified."
        )
    
    report = f"A {fracture_type} fracture has been detected in the {bone}"
    if location:
        report += f", located at the {location}"
    report += "."
    
    if severity:
        report += f" The fracture shows {severity} severity."
        
    report += " It is recommended to consult a medical professional for further evaluation and treatment."
    
    return report

async def generate_grok_report(
    bone: Optional[str], 
    location: Optional[str], 
    fracture_type: Optional[str], 
    severity: Optional[str]
) -> str:
    try:
        prompt_parts = [f"Bone: {bone}", f"Fracture type: {fracture_type}"]
        if location:
            prompt_parts.append(f"Location: {location}")
        if severity:
            prompt_parts.append(f"Severity: {severity}")
            
        findings = ", ".join(prompt_parts)
        prompt = (
            f"Based on the following findings: {findings}. "
            "Write a single professional, radiology-style paragraph (2-4 sentences) describing these fracture findings. "
            "Do not include any extra commentary, disclaimers, or markdown formatting in your response."
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.GROK_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.GROK_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except Exception:
        return generate_template_report(bone, location, fracture_type, severity)