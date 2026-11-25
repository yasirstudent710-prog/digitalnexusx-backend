import os, json, csv, io, hashlib, hmac, base64, time
from datetime import datetime, date
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./digitalnexusx.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def hash_pw(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(h).decode()

def verify_pw(pw: str, stored: str) -> bool:
    try:
        s, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), base64.b64decode(s), 200000)
        return hmac.compare_digest(base64.b64encode(calc).decode(), h)
    except Exception:
        return False

def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def make_token(username: str) -> str:
    header = b64u(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    payload = b64u(json.dumps({"sub": username, "exp": int(time.time())+86400*7}).encode())
    sig = b64u(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

def check_token(auth: Optional[str] = Header(None, alias="Authorization")):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Token required")
    token = auth[7:]
    try:
        header, payload, sig = token.split(".")
        expected = b64u(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(401, "Invalid token")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data.get("exp", 0) < int(time.time()):
            raise HTTPException(401, "Token expired")
        return data["sub"]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid token")

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True); name = Column(String(200), nullable=False)
    phone = Column(String(100), default=""); email = Column(String(200), default="")
    service = Column(String(200), default=""); message = Column(Text, default="")
    status = Column(String(50), default="New"); notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class Consultation(Base):
    __tablename__ = "consultations"
    id = Column(Integer, primary_key=True); name = Column(String(200), nullable=False)
    phone = Column(String(100), default=""); email = Column(String(200), default="")
    service = Column(String(200), default=""); preferred_date = Column(String(100), default="")
    notes = Column(Text, default=""); status = Column(String(50), default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True); username = Column(String(100), unique=True)
    hashed_password = Column(String(500))

class SiteStats(Base):
    __tablename__ = "site_stats"
    id = Column(Integer, primary_key=True); leads_generated = Column(Integer, default=0)
    sales_delivered = Column(Integer, default=0); cost_per_lead = Column(Float, default=0)
    roas = Column(Float, default=0); growth_percent = Column(Float, default=0)

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True); title = Column(String(200))
    description = Column(Text, default=""); features = Column(Text, default="")
    turnaround = Column(String(100), default=""); sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

class Faq(Base):
    __tablename__ = "faqs"
    id = Column(Integer, primary_key=True); question = Column(Text)
    answer = Column(Text, default=""); sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

class SiteSetting(Base):
    __tablename__ = "site_settings"
    id = Column(Integer, primary_key=True); key = Column(String(100), unique=True)
    value = Column(Text, default="")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def seed(db: Session):
    if not db.query(AdminUser).filter_by(username=ADMIN_USERNAME).first():
        db.add(AdminUser(username=ADMIN_USERNAME, hashed_password=hash_pw(ADMIN_PASSWORD)))
    if not db.query(SiteStats).first():
        db.add(SiteStats(leads_generated=0, sales_delivered=0, cost_per_lead=0, roas=0, growth_percent=0))
    services = [
        ("Shopify Web Development","Custom high-converting Shopify & Shopify Plus stores, bespoke Liquid themes, and checkout optimization.","Custom Shopify 2.0 & Plus Theme Development | High-Converting Product Page Architecture | App Integrations & Custom Upsell Funnels","1 - 3 Weeks"),
        ("E-Commerce Startup","All-in-one startup launch: store build, winning product hunting, sourcing, shoot, social setup, and paid ads.","Shopify & WooCommerce | Product Hunting | Product Sourcing (Local & Chinese Supplier)","2 - 4 Weeks Setup"),
        ("WooCommerce Development","Scalable WordPress & WooCommerce stores with custom plugins, fast caching, and secure payments.","Custom Theme & Child-Theme | Custom Plugin & REST API | High-Speed Caching","1 - 3 Weeks"),
        ("Web Development","Complete full-stack engineering: modern frontend, scalable backend APIs, databases, and cloud.","React/Next.js/TypeScript | Node/Python/PHP APIs | PostgreSQL/MySQL/MongoDB","2 - 4 Weeks"),
        ("Product & Business Shoot","High-end commercial 4K photography, lifestyle shoots, corporate visuals, and ad-ready reels.","White Background Studio Shoots | Lifestyle Photography | Corporate Brand Shoots","3 - 7 Days"),
        ("Meta Ads","High-ROAS Facebook & Instagram ad scaling, creative testing, and CAPI tracking.","Meta Ads Setup | Advantage+ & CBO Scaling | Pixel & Conversion API (CAPI)","Ongoing / Scaled"),
        ("Google Ads","High-intent Google Search, Shopping, Performance Max, and YouTube campaigns.","Performance Max | Search & Keyword Targeting | Merchant Center Setup","Ongoing / Scaled"),
        ("TikTok Ads","Viral UGC creatives, Spark Ads, and TikTok Shop campaign scaling.","UGC Video Creatives | Spark Ads | TikTok Shop Integration","Ongoing / Scaled"),
        ("Dropshipping Internationally","End-to-end global supply chain, winning product sourcing, multi-country fulfillment.","Product Sourcing & Trend Analysis | Private Agent 5-8 Day Shipping | Multi-Country Stores","1 - 2 Weeks Setup"),
    ]
    if not db.query(Service).first():
        for i,(t,d,f,turn) in enumerate(services): db.add(Service(title=t,description=d,features=f,turnaround=turn,sort_order=i))
    faqs = [
        ("How long does a Shopify store take?","Most Shopify stores are delivered in 1-3 weeks depending on products and custom features."),
        ("Do you require a lock-in contract?","No. We offer transparent reporting and weekly optimization with no lock-in contracts."),
        ("Do you provide a free strategy audit?","Yes, book a consultation and we will provide a free strategy audit and custom roadmap."),
        ("How soon do you reply?","We reply within 24 hours via phone, WhatsApp or email."),
    ]
    if not db.query(Faq).first():
        for i,(q,a) in enumerate(faqs): db.add(Faq(question=q,answer=a,sort_order=i))
    settings = {"phone":"+92 322 1526000","whatsapp":"+92 322 1526000","email":"digitalnexusxpk@gmail.com","office":"DHA Phase 1, Lahore, Pakistan"}
    for k,v in settings.items():
        if not db.query(SiteSetting).filter_by(key=k).first(): db.add(SiteSetting(key=k,value=v))
    db.commit()

with SessionLocal() as _db: seed(_db)

app = FastAPI(title="DigitalNexusX API")
origins = os.getenv("ALLOWED_ORIGINS","https://digitalnexusx.com,https://www.digitalnexusx.com,http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in origins], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

# Schemas
class LeadIn(BaseModel):
    name: str; phone: str = ""; email: str = ""; service: str = ""; message: str = ""
class LeadUpdate(BaseModel):
    status: Optional[str] = None; notes: Optional[str] = None
class ConsultIn(BaseModel):
    name: str; phone: str = ""; email: str = ""; service: str = ""; preferred_date: str = ""; notes: str = ""
class ConsultUpdate(BaseModel):
    status: str
class LoginIn(BaseModel):
    username: str; password: str
class StatsIn(BaseModel):
    leads_generated: int = 0; sales_delivered: int = 0; cost_per_lead: float = 0; roas: float = 0; growth_percent: float = 0
class ServiceIn(BaseModel):
    title: str; description: str = ""; features: str = ""; turnaround: str = ""; sort_order: int = 0; is_active: bool = True
class FaqIn(BaseModel):
    question: str; answer: str = ""; sort_order: int = 0; is_active: bool = True
class SettingsIn(BaseModel):
    phone: str = ""; whatsapp: str = ""; email: str = ""; office: str = ""

def lead_dict(x): return {"id":x.id,"name":x.name,"phone":x.phone,"email":x.email,"service":x.service,"message":x.message,"status":x.status,"notes":x.notes or "","created_at":x.created_at.isoformat() if x.created_at else None}
def consult_dict(x): return {"id":x.id,"name":x.name,"phone":x.phone,"email":x.email,"service":x.service,"preferred_date":x.preferred_date,"notes":x.notes,"status":x.status,"created_at":x.created_at.isoformat() if x.created_at else None}
def service_dict(x): return {"id":x.id,"title":x.title,"description":x.description,"features":x.features,"turnaround":x.turnaround,"sort_order":x.sort_order,"is_active":x.is_active}
def faq_dict(x): return {"id":x.id,"question":x.question,"answer":x.answer,"sort_order":x.sort_order,"is_active":x.is_active}
def stats_dict(x): return {"leads_generated":x.leads_generated,"sales_delivered":x.sales_delivered,"cost_per_lead":x.cost_per_lead,"roas":x.roas,"growth_percent":x.growth_percent}

@app.get("/health")
def health(): return {"status":"ok","service":"DigitalNexusX API"}

@app.get("/admin")
def admin_page(): return FileResponse("static/admin.html")

@app.post("/api/leads")
def create_lead(data: LeadIn, db: Session = Depends(get_db)):
    obj = Lead(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return lead_dict(obj)

@app.post("/api/consultations")
def create_consult(data: ConsultIn, db: Session = Depends(get_db)):
    obj = Consultation(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return consult_dict(obj)

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    s = db.query(SiteStats).first(); return stats_dict(s) if s else {}

@app.get("/api/services")
def get_services(db: Session = Depends(get_db)):
    return [service_dict(x) for x in db.query(Service).filter_by(is_active=True).order_by(Service.sort_order).all()]

@app.get("/api/faqs")
def get_faqs(db: Session = Depends(get_db)):
    return [faq_dict(x) for x in db.query(Faq).filter_by(is_active=True).order_by(Faq.sort_order).all()]

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    return {x.key:x.value for x in db.query(SiteSetting).all()}

@app.post("/api/admin/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.query(AdminUser).filter_by(username=data.username).first()
    if not u or not verify_pw(data.password, u.hashed_password): raise HTTPException(401, "Invalid username or password")
    return {"access_token": make_token(u.username), "token_type":"bearer", "username": u.username}

@app.get("/api/admin/dashboard")
def dashboard(db: Session = Depends(get_db), user: str = Depends(check_token)):
    total = db.query(Lead).count()
    today = db.query(Lead).filter(Lead.created_at >= datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)).count()
    new = db.query(Lead).filter_by(status="New").count()
    converted = db.query(Lead).filter_by(status="Converted").count()
    recent = db.query(Lead).order_by(Lead.id.desc()).limit(5).all()
    return {"total_leads":total,"leads_today":today,"new_leads":new,"converted":converted,"conversion_percent": round((converted/total*100) if total else 0,2),"recent_leads":[lead_dict(x) for x in recent],"total_consultations":db.query(Consultation).count()}

@app.get("/api/admin/leads/export")
def export_leads(db: Session = Depends(get_db), user: str = Depends(check_token)):
    out = io.StringIO(); w = csv.writer(out); w.writerow(["id","name","phone","email","service","message","status","created_at"])
    for x in db.query(Lead).order_by(Lead.id.desc()).all(): w.writerow([x.id,x.name,x.phone,x.email,x.service,x.message,x.status,x.created_at])
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=leads.csv"})

@app.get("/api/admin/leads")
def list_leads(search: str = "", status: str = "", db: Session = Depends(get_db), user: str = Depends(check_token)):
    q = db.query(Lead)
    if status: q = q.filter_by(status=status)
    if search: q = q.filter((Lead.name.contains(search))|(Lead.email.contains(search))|(Lead.phone.contains(search)))
    return [lead_dict(x) for x in q.order_by(Lead.id.desc()).all()]

@app.put("/api/admin/leads/{lead_id}")
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Lead).get(lead_id)
    if not x: raise HTTPException(404, "Lead not found")
    if data.status is not None:
        if data.status not in ["New","Contacted","Qualified","Converted","Lost"]: raise HTTPException(400, "Invalid status")
        x.status = data.status
    if data.notes is not None: x.notes = data.notes
    db.commit(); db.refresh(x); return lead_dict(x)

@app.delete("/api/admin/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Lead).get(lead_id)
    if not x: raise HTTPException(404, "Lead not found")
    db.delete(x); db.commit(); return {"deleted": True}

@app.get("/api/admin/consultations")
def list_consults(db: Session = Depends(get_db), user: str = Depends(check_token)):
    return [consult_dict(x) for x in db.query(Consultation).order_by(Consultation.id.desc()).all()]

@app.put("/api/admin/consultations/{cid}")
def update_consult(cid: int, data: ConsultUpdate, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Consultation).get(cid)
    if not x: raise HTTPException(404, "Not found")
    x.status = data.status; db.commit(); db.refresh(x); return consult_dict(x)

@app.get("/api/admin/services")
def admin_services(db: Session = Depends(get_db), user: str = Depends(check_token)):
    return [service_dict(x) for x in db.query(Service).order_by(Service.sort_order).all()]

@app.post("/api/admin/services")
def create_service(data: ServiceIn, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = Service(**data.model_dump()); db.add(x); db.commit(); db.refresh(x); return service_dict(x)

@app.put("/api/admin/services/{sid}")
def update_service(sid: int, data: ServiceIn, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Service).get(sid)
    if not x: raise HTTPException(404, "Not found")
    for k,v in data.model_dump().items(): setattr(x,k,v)
    db.commit(); db.refresh(x); return service_dict(x)

@app.delete("/api/admin/services/{sid}")
def delete_service(sid: int, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Service).get(sid)
    if not x: raise HTTPException(404, "Not found")
    db.delete(x); db.commit(); return {"deleted": True}

@app.get("/api/admin/faqs")
def admin_faqs(db: Session = Depends(get_db), user: str = Depends(check_token)):
    return [faq_dict(x) for x in db.query(Faq).order_by(Faq.sort_order).all()]

@app.post("/api/admin/faqs")
def create_faq(data: FaqIn, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = Faq(**data.model_dump()); db.add(x); db.commit(); db.refresh(x); return faq_dict(x)

@app.put("/api/admin/faqs/{fid}")
def update_faq(fid: int, data: FaqIn, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Faq).get(fid)
    if not x: raise HTTPException(404, "Not found")
    for k,v in data.model_dump().items(): setattr(x,k,v)
    db.commit(); db.refresh(x); return faq_dict(x)

@app.delete("/api/admin/faqs/{fid}")
def delete_faq(fid: int, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(Faq).get(fid)
    if not x: raise HTTPException(404, "Not found")
    db.delete(x); db.commit(); return {"deleted": True}

@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(get_db), user: str = Depends(check_token)):
    return stats_dict(db.query(SiteStats).first())

@app.put("/api/admin/stats")
def update_stats(data: StatsIn, db: Session = Depends(get_db), user: str = Depends(check_token)):
    x = db.query(SiteStats).first()
    for k,v in data.model_dump().items(): setattr(x,k,v)
    db.commit(); return stats_dict(x)

@app.get("/api/admin/settings")
def admin_settings(db: Session = Depends(get_db), user: str = Depends(check_token)):
    return {x.key:x.value for x in db.query(SiteSetting).all()}

@app.put("/api/admin/settings")
def update_settings(data: SettingsIn, db: Session = Depends(get_db), user: str = Depends(check_token)):
    for k,v in data.model_dump().items():
        row = db.query(SiteSetting).filter_by(key=k).first()
        if row: row.value = v
        else: db.add(SiteSetting(key=k, value=v))
    db.commit(); return {x.key:x.value for x in db.query(SiteSetting).all()}
