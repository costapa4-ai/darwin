"""
UI Automation API Routes
Browser automation and visual understanding endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from consciousness.ui_automation import (
    get_ui_automation_engine,
    BrowsingIntent
)

router = APIRouter(prefix="/api/v1/ui", tags=["ui-automation"])


class NavigateRequest(BaseModel):
    """Request to navigate to a URL"""
    url: str
    start_session: bool = False
    intent: str = "exploration"


class ClickRequest(BaseModel):
    """Request to click an element"""
    selector: str


class TypeRequest(BaseModel):
    """Request to type text"""
    selector: str
    text: str


class ScrollRequest(BaseModel):
    """Request to scroll"""
    direction: str = "down"
    amount: int = 500


class ScreenshotRequest(BaseModel):
    """Request to take a screenshot"""
    filename: Optional[str] = None
    full_page: bool = False
    element_selector: Optional[str] = None


class DiscoveryRequest(BaseModel):
    """Request to record a discovery"""
    content: str
    discovery_type: str = "concept"
    capture_visual: bool = True


class ExploreRequest(BaseModel):
    """Request to autonomously explore"""
    url: str
    topic: str
    max_pages: int = 5


@router.get("/status")
async def get_ui_status():
    """
    Get UI automation engine status

    Returns browser state, active session, and statistics
    """
    engine = get_ui_automation_engine()
    if not engine:
        return {
            'success': True,
            'enabled': False,
            'message': 'UI automation not initialized'
        }

    return {
        'success': True,
        'enabled': True,
        **engine.get_stats()
    }


@router.post("/browser/start")
async def start_browser():
    """Start the Playwright browser"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    success = await engine.start_browser()
    if success:
        return {
            'success': True,
            'message': 'Browser started'
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to start browser. Ensure Playwright is installed."
        )


@router.post("/browser/stop")
async def stop_browser():
    """Stop the browser"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    await engine.stop_browser()
    return {
        'success': True,
        'message': 'Browser stopped'
    }


@router.post("/navigate")
async def navigate(request: NavigateRequest):
    """
    Navigate to a URL

    Optionally starts a new session with specified intent
    """
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    try:
        if request.start_session:
            # Validate intent
            try:
                intent = BrowsingIntent(request.intent)
            except ValueError:
                intent = BrowsingIntent.EXPLORATION

            session = await engine.start_session(request.url, intent)
            return {
                'success': True,
                'session': session.to_dict(),
                'url': request.url
            }
        else:
            result = await engine.navigate(request.url)
            return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click")
async def click_element(request: ClickRequest):
    """Click an element by selector"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    result = await engine.click(request.selector)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


@router.post("/type")
async def type_text(request: TypeRequest):
    """Type text into an element"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    result = await engine.type_text(request.selector, request.text)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


@router.post("/scroll")
async def scroll_page(request: ScrollRequest):
    """Scroll the page"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    result = await engine.scroll(request.direction, request.amount)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


@router.post("/screenshot")
async def take_screenshot(request: ScreenshotRequest):
    """Take a screenshot of the current page"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    try:
        result = await engine.take_screenshot(
            filename=request.filename,
            full_page=request.full_page,
            element_selector=request.element_selector
        )
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_page():
    """
    Analyze the current page using AI vision

    Extracts content type, key concepts, code examples, etc.
    """
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    try:
        result = await engine.analyze_page()
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discovery")
async def record_discovery(request: DiscoveryRequest):
    """
    Record a discovery from the current page

    Captures visual context and stores for later learning
    """
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    try:
        discovery = await engine.extract_discovery(
            content=request.content,
            discovery_type=request.discovery_type,
            capture_visual=request.capture_visual
        )
        return {
            'success': True,
            'discovery': discovery.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explore")
async def autonomous_explore(request: ExploreRequest):
    """
    Autonomously explore a website to learn about a topic

    Darwin will navigate, analyze, and extract discoveries
    """
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    try:
        result = await engine.autonomous_explore(
            start_url=request.url,
            topic=request.topic,
            max_pages=min(request.max_pages, 10)  # Limit max pages
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discoveries")
async def get_discoveries(limit: int = 20):
    """Get recent visual discoveries"""
    engine = get_ui_automation_engine()
    if not engine:
        return {
            'success': True,
            'discoveries': [],
            'count': 0
        }

    discoveries = engine.get_discoveries(limit)
    return {
        'success': True,
        'discoveries': discoveries,
        'count': len(discoveries)
    }


@router.get("/sessions")
async def get_sessions(limit: int = 10):
    """Get recent browsing sessions"""
    engine = get_ui_automation_engine()
    if not engine:
        return {
            'success': True,
            'sessions': [],
            'count': 0
        }

    sessions = engine.get_sessions(limit)
    return {
        'success': True,
        'sessions': sessions,
        'count': len(sessions)
    }


@router.post("/session/end")
async def end_session(session_id: Optional[str] = None):
    """End the current or specified browsing session"""
    engine = get_ui_automation_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="UI automation not available")

    try:
        session = await engine.end_session(session_id)
        return {
            'success': True,
            'session': session.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def initialize_ui_automation(engine):
    """Initialize UI automation with engine instance"""
    from consciousness.ui_automation import set_ui_automation_engine
    if engine:
        set_ui_automation_engine(engine)
