"""
Funding Management Router - Admin GUI and API
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db_session
from app.core.security import require_admin
from app.core.capabilities import require_capability
from .models import FundingSource, FundingApplication, FundingTask, FundingSourceType, ApplicationStatus

router = APIRouter(
    prefix="/admin/funding",
    tags=["funding_management"],
    dependencies=[Depends(require_admin), Depends(require_capability("admin_funding"))]
)


@router.get("/", response_class=HTMLResponse)
async def funding_dashboard(request: Request):
    """Main funding management dashboard."""
    
    # Get stats from database (using static values for now - implement queries as needed)
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import AsyncSession
    
    try:
        async with get_db_session() as session:
            # Count active sources
            result = await session.execute(
                select(func.count()).select_from(FundingSource).where(FundingSource.is_active == True)
            )
            active_sources = result.scalar() or 0
            
            # Count pending applications
            result = await session.execute(
                select(func.count()).select_from(FundingApplication)
                .where(FundingApplication.status.in_([
                    ApplicationStatus.SUBMITTED, 
                    ApplicationStatus.UNDER_REVIEW
                ]))
            )
            pending_apps = result.scalar() or 0
            
            # Count awarded applications
            result = await session.execute(
                select(func.count()).select_from(FundingApplication)
                .where(FundingApplication.status == ApplicationStatus.AWARDED)
            )
            secured = result.scalar() or 0
    except Exception:
        # Database tables may not exist yet - return zeros
        active_sources = 0
        pending_apps = 0
        secured = 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Semptify Funding Management</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .card h3 {{ margin-top: 0; color: #2c3e50; }}
            .stat {{ font-size: 2.5em; font-weight: bold; color: #27ae60; margin: 10px 0; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
            .btn:hover {{ background: #2980b9; }}
            .nav {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .nav a {{ margin-right: 20px; color: #3498db; text-decoration: none; font-weight: 500; }}
            .nav a:hover {{ text-decoration: underline; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: 600; }}
            .status-pill {{ padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 500; }}
            .status-prospect {{ background: #e3f2fd; color: #1976d2; }}
            .status-submitted {{ background: #fff3e0; color: #f57c00; }}
            .status-awarded {{ background: #e8f5e9; color: #388e3c; }}
            .status-declined {{ background: #ffebee; color: #d32f2f; }}
            .priority-high {{ color: #d32f2f; font-weight: bold; }}
            .priority-medium {{ color: #f57c00; }}
            .priority-low {{ color: #388e3c; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💰 Semptify Funding Management</h1>
                <p>Admin tool for tracking funding sources, applications, and budgets</p>
            </div>
            
            <div class="nav">
                <a href="/admin/funding/">📊 Dashboard</a>
                <a href="/admin/funding/sources">🏦 Funding Sources</a>
                <a href="/admin/funding/applications">📝 Applications</a>
                <a href="/admin/funding/budget">💵 Budget</a>
                <a href="/admin/funding/prospectus">📄 ID System Prospectus</a>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>🏦 Active Prospects</h3>
                    <div class="stat">{active_sources}</div>
                    <p>Potential funding sources identified and active</p>
                    <a href="/admin/funding/sources" class="btn">Manage Sources</a>
                </div>
                
                <div class="card">
                    <h3>⏳ Pending Applications</h3>
                    <div class="stat">{pending_apps}</div>
                    <p>Applications submitted or currently under review</p>
                    <a href="/admin/funding/applications" class="btn">Track Applications</a>
                </div>
                
                <div class="card">
                    <h3>✅ Secured Awards</h3>
                    <div class="stat">{secured}</div>
                    <p>Successfully funded applications</p>
                    <a href="/admin/funding/applications?status=awarded" class="btn">View Awards</a>
                </div>
                
                <div class="card">
                    <h3>🔐 Secured ID System</h3>
                    <div class="stat" style="font-size: 1.5em; color: #3498db;">PLANNED</div>
                    <p>Cryptographic document verification system pending funding</p>
                    <a href="/admin/funding/prospectus" class="btn">View Prospectus</a>
                </div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>🎯 Priority Actions</h3>
                <ul>
                    <li><strong>LSC Grant:</strong> Legal Services Corporation application - Deadline approaching</li>
                    <li><strong>Suffolk LIT Lab:</strong> Partnership discussion - Technical credibility</li>
                    <li><strong>Ford Foundation:</strong> Housing justice program - Long-term funding</li>
                    <li><strong>Secured ID Documentation:</strong> Technical prospectus for infrastructure funders</li>
                </ul>
                <a href="/admin/funding/sources/new" class="btn">Add New Funding Source</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@router.get("/prospectus", response_class=HTMLResponse)
async def funding_prospectus(request: Request):
    """Display the ID System Funding Prospectus."""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Semptify Secured ID System - Funding Prospectus</title>
        <style>
            body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; line-height: 1.6; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 40px; }
            h1 { color: #2c3e50; margin-bottom: 10px; }
            h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 40px; }
            h3 { color: #34495e; margin-top: 30px; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f8f9fa; font-weight: 600; }
            .highlight { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .btn { display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; }
            .btn:hover { background: #2980b9; }
            .nav { margin-bottom: 30px; }
            .nav a { color: #3498db; text-decoration: none; }
            ul li { margin: 8px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/admin/funding/">← Back to Funding Dashboard</a>
            </div>
            
            <div class="header">
                <h1>🔐 Semptify Secured ID System</h1>
                <h2>Funding Prospectus</h2>
                <p><strong>Semptify — Tenant Rights Advocate Organization</strong></p>
            </div>
            
            <h2>Executive Summary</h2>
            <p>Semptify has designed a cryptographic identity and document verification system 
            ("Semptify Secured ID") that will implement upon funding. This system protects 
            tenant privacy while establishing provable document authenticity—a critical need 
            for housing court proceedings.</p>
            
            <div class="highlight">
                <strong>Mission Alignment:</strong> We advocate for tenants exercising their 
                lawful rights—not tenants breaking the law. Our technology serves lawful 
                documentation and rights protection.
            </div>
            
            <h2>Current State (Demonstration Prototype)</h2>
            <p><strong>Implemented:</strong></p>
            <ul>
                <li>✅ Functional ID generation for users and documents</li>
                <li>✅ Privacy-preserving architecture (user-controlled vault storage)</li>
                <li>✅ Stateless design with no centralized data harvesting</li>
                <li>✅ Demonstration-grade identifiers suitable for beta testing</li>
            </ul>
            
            <h2>Post-Funding Implementation</h2>
            
            <h3>Technical Components</h3>
            <p><strong>1. Cryptographically Signed Identifiers</strong></p>
            <ul>
                <li>HMAC-SHA256 signatures using server-side secret keys</li>
                <li>Tamper-proof binding between document and timestamp</li>
                <li>Clone-resistant server authentication</li>
            </ul>
            
            <p><strong>2. Document Integrity Verification ("Vault Witness")</strong></p>
            <ul>
                <li>SHA-256 content hashing at upload</li>
                <li>RFC 3161 trusted timestamp integration (court-admissible)</li>
                <li>Immutable provenance chain</li>
            </ul>
            
            <p><strong>3. Privacy-Preserving Architecture</strong></p>
            <ul>
                <li>Salt-based ID generation</li>
                <li>No global lookup table—resolution only within tenant's vault</li>
                <li>User anonymity preserved even if document ID leaks</li>
            </ul>
            
            <h2>Security Guarantees</h2>
            <table>
                <tr>
                    <th>Threat</th>
                    <th>Protection</th>
                </tr>
                <tr>
                    <td>Server impersonation</td>
                    <td>HMAC signatures verify authentic Semptify infrastructure</td>
                </tr>
                <tr>
                    <td>Document tampering</td>
                    <td>Content hash detects any modification post-upload</td>
                </tr>
                <tr>
                    <td>ID forgery</td>
                    <td>Secret salt prevents generation of valid IDs by attackers</td>
                </tr>
                <tr>
                    <td>Timeline manipulation</td>
                    <td>Cryptographic timestamps establish chronological order</td>
                </tr>
            </table>
            
            <h2>Budget Estimate</h2>
            <table>
                <tr>
                    <th>Component</th>
                    <th>Timeline</th>
                </tr>
                <tr>
                    <td>Cryptographic ID implementation</td>
                    <td>2-3 months</td>
                </tr>
                <tr>
                    <td>RFC 3161 timestamp integration</td>
                    <td>1 month</td>
                </tr>
                <tr>
                    <td>Security audit</td>
                    <td>1 month</td>
                </tr>
                <tr>
                    <td>Legal admissibility documentation</td>
                    <td>1 month</td>
                </tr>
                <tr>
                    <td><strong>Total</strong></td>
                    <td><strong>4-6 months</strong></td>
                </tr>
            </table>
            
            <div class="highlight">
                <strong>Differentiation:</strong> Unlike commercial tenant screening tools 
                (which centralize data and create privacy risks), Semptify Secured ID keeps 
                tenant data in tenant-controlled storage, proves authenticity without exposing 
                content, and respects tenant privacy as a first-class design constraint.
            </div>
            
            <h2>Contact</h2>
            <p>For funding inquiries or partnership discussions, contact the Semptify 
            administrative team.</p>
            
            <hr style="margin: 40px 0;">
            <p style="text-align: center; color: #666;">
                <strong>Semptify Project — Tenant Rights Advocate Organization</strong><br>
                <em>Document Everything. Avoid the Pitfalls. Tenant advocacy, not neutrality.</em>
            </p>
        </div>
    </body>
    </html>
    """
    return html
