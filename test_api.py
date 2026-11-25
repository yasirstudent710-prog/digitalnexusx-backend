import json, urllib.request, os
BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")
def call(method, path, data=None, token=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE+path, data=body, method=method, headers={"Content-Type":"application/json", **({"Authorization":"Bearer "+token} if token else {})})
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b"{}")
h = call("GET","/health"); assert h["status"]=="ok", h; print("health OK", h)
lead = call("POST","/api/leads",{"name":"Test Client","phone":"+92 300 0000000","email":"test@example.com","service":"Meta Ads","message":"I want leads"}); assert lead["id"]; print("lead created", lead["id"])
cons = call("POST","/api/consultations",{"name":"Test Client","phone":"+92 300 0000000","service":"Shopify","preferred_date":"2026-12-01"}); assert cons["id"]; print("consultation created")
login = call("POST","/api/admin/login",{"username":os.getenv("ADMIN_USERNAME","admin"),"password":os.getenv("ADMIN_PASSWORD","admin123")}); token=login["access_token"]; assert token; print("login OK")
dash1 = call("GET","/api/admin/dashboard",token=token); assert dash1["total_leads"]>=1; print("dashboard", dash1)
upd = call("PUT",f"/api/admin/leads/{lead['id']}",{"status":"Qualified"},token=token); assert upd["status"]=="Qualified"; print("lead status updated")
call("PUT","/api/admin/stats",{"leads_generated":123,"sales_delivered":45,"cost_per_lead":999,"roas":3.5,"growth_percent":32},token=token)
stats = call("GET","/api/stats"); assert stats["leads_generated"]==123 and stats["roas"]==3.5, stats; print("stats updated & public read OK", stats)
services = call("GET","/api/services"); assert len(services)>=9, len(services); print("services OK", len(services))
print("ALL TESTS PASSED")
