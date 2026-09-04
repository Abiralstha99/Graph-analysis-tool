from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import base64
import io
import tempfile
import json
import traceback
import json
import time

from .config import Settings
from .services.graph_statistics import summarize_series
from .services.analysis_service import AnalysisService

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

try:
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    pd = None
    plt = None

try:
    from utils.plotter import process_file
except ImportError:
    def process_file(upload_file):
        """Fallback process_file function"""
        import pandas as pd
        df = pd.read_csv(upload_file.file, header=1)
        return df

router = APIRouter(prefix="/analysis", tags=["Graph Analysis"])

def generate_graph_image(baseline_df, sample_df, sample_name: str) -> bytes:
    """Generate a graph image for AI analysis"""
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create the comparison plot
        ax.plot(baseline_df.iloc[:, 0], baseline_df.iloc[:, 1], 'b-', linewidth=2, label='Baseline')
        ax.plot(sample_df.iloc[:, 0], sample_df.iloc[:, 1], 'r-', linewidth=2, label=f'Sample: {sample_name}')
        
        ax.set_xlabel('X-axis')
        ax.set_ylabel('Y-axis')
        ax.set_title(f'Baseline vs {sample_name} Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Save to bytes
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='PNG', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_bytes = img_buffer.read()
        
        plt.close(fig)
        return img_bytes
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating graph image: {str(e)}")

def analyze_data_statistics(baseline_df, sample_df, sample_name: str) -> dict:
    """Generate statistical summary of the data"""
    try:
        stats = summarize_series(
            baseline_df.iloc[:, 1].tolist(), sample_df.iloc[:, 1].tolist()
        )
        stats["sample_name"] = sample_name
        stats["baseline_stats"]["range_x"] = [
            float(baseline_df.iloc[:, 0].min()),
            float(baseline_df.iloc[:, 0].max()),
        ]
        stats["sample_stats"]["range_x"] = [
            float(sample_df.iloc[:, 0].min()),
            float(sample_df.iloc[:, 0].max()),
        ]
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing statistics: {str(e)}")

@router.post("/ftir/analyze")
async def generate_graph_insights(
    baseline: UploadFile = File(...),
    sample: UploadFile = File(...),
    sample_name: Optional[str] = Form(None)
):
    """
    Generate AI-powered insights and analysis for a graph comparison between baseline and sample data
    """
    try:
        # Check if required modules are available
        if not GENAI_AVAILABLE:
            return JSONResponse(
                status_code=500, 
                content={"error": "Google Generative AI library not available"}
            )
        
        if not MATPLOTLIB_AVAILABLE:
            return JSONResponse(
                status_code=500, 
                content={"error": "Matplotlib library not available"}
            )
        
        settings = Settings.from_environment()
        if not settings.gemini_api_key:
            return JSONResponse(
                status_code=500, 
                content={"error": "Gemini AI API key not configured"}
            )

        genai.configure(api_key=settings.gemini_api_key)
        
        # Process uploaded files
        try:
            baseline_df = process_file(baseline)
            sample_df = process_file(sample)
        except Exception as e:
            return JSONResponse(
                status_code=400, 
                content={"error": f"Failed to process uploaded files: {str(e)}"}
            )
        
        # Use filename if sample_name not provided
        if not sample_name:
            sample_name = sample.filename.split('.')[0] if sample.filename else "Unknown Sample"
        
        # Generate statistical analysis
        try:
            stats = analyze_data_statistics(baseline_df, sample_df, sample_name)
        except Exception as e:
            return JSONResponse(
                status_code=500, 
                content={"error": f"Failed to analyze statistics: {str(e)}"}
            )
        
        # Generate graph image for AI analysis
        try:
            graph_bytes = generate_graph_image(baseline_df, sample_df, sample_name)
            graph_b64 = base64.b64encode(graph_bytes).decode()
        except Exception as e:
            return JSONResponse(
                status_code=500, 
                content={"error": f"Failed to generate graph image: {str(e)}"}
            )
        
        # Configure Gemini model with fallback
        model = None
        model_names = ['models/gemini-2.5-flash','models/gemini-pro', 'gemini-pro', 'models/gemini-1.0-pro', 'gemini-1.0-pro-latest']
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except Exception as e:
                continue
        
        if model is None:
            # Provide statistical analysis without AI insights
            try:
                from datetime import datetime
                analysis_result = {
                    "sample_name": sample_name,
                    "statistics": stats,
                    "ai_insights": f"""**Infrared Grease Analysis - Statistical Summary**

**Grease Condition Assessment:**
- Baseline (Fresh Grease): Mean={stats['baseline_stats']['mean_y']:.3f} ± {stats['baseline_stats']['std_y']:.3f}
- Sample ({sample_name}): Mean={stats['sample_stats']['mean_y']:.3f} ± {stats['sample_stats']['std_y']:.3f}
- Spectral Difference: {stats['differences']['mean_diff']:.3f} absorption units

**Preliminary Oxidation Analysis:**
{"⚠️ Significant spectral changes detected - potential grease degradation or contamination" if abs(stats['differences']['mean_diff']) > stats['baseline_stats']['std_y'] else "✓ Spectral patterns within normal range - grease condition appears stable"}

**Equipment Maintenance Status:** 
Based on statistical analysis, {"immediate inspection recommended" if abs(stats['differences']['mean_diff']) > 2 * stats['baseline_stats']['std_y'] else "continue monitoring" if abs(stats['differences']['mean_diff']) > stats['baseline_stats']['std_y'] else "grease condition acceptable"}

**Note:** This statistical analysis provides preliminary grease assessment for your infrared spectroscopy data. Full AI-powered analysis will provide detailed oxidation markers, water contamination detection, and specific maintenance recommendations when the AI service is available.""",
                    "metadata": {
                        "baseline_file": baseline.filename,
                        "sample_file": sample.filename,
                        "analysis_timestamp": datetime.now().isoformat(),
                        "status": "statistical_only"
                    }
                }
                
                return JSONResponse(content=analysis_result)
            except Exception as e:
                return JSONResponse(
                    status_code=500, 
                    content={"error": f"Failed to prepare statistical analysis: {str(e)}"}
                )
        
        # Create detailed prompt for infrared grease analysis
        prompt = f"""
        Analyze this infrared spectroscopy data for grease oxidation analysis comparing baseline (fresh grease) and sample data ({sample_name}).
        
        Statistical Summary:
        - Baseline: Mean={stats['baseline_stats']['mean_y']:.3f}, Std={stats['baseline_stats']['std_y']:.3f}, Range=[{stats['baseline_stats']['min_y']:.3f}, {stats['baseline_stats']['max_y']:.3f}]
        - Sample: Mean={stats['sample_stats']['mean_y']:.3f}, Std={stats['sample_stats']['std_y']:.3f}, Range=[{stats['sample_stats']['min_y']:.3f}, {stats['sample_stats']['max_y']:.3f}]
        - Mean Difference: {stats['differences']['mean_diff']:.3f}
        
        **Context**: This is infrared light analysis through grease samples to determine oxidation levels, lifecycle stage, and potential contamination or degradation issues.
        
        Please provide specialized grease analysis focusing on:
        1. **Oxidation Assessment**: Analyze spectral changes indicating grease oxidation levels. Look for characteristic IR absorption bands around 1700-1750 cm⁻¹ (C=O stretch) that increase with oxidation.
        2. **Grease Lifecycle Stage**: Determine the degradation stage based on spectral changes. Fresh grease vs. aged/oxidized grease patterns.
        3. **Contamination Detection**: Identify potential water contamination (broad O-H stretch around 3200-3600 cm⁻¹) or other foreign substances affecting grease quality.
        4. **Fault Analysis**: Assess if deviations from baseline indicate grease failure, unusual wear patterns, or maintenance issues.
        5. **Quality Comparison**: Compare sample against baseline to determine if grease is within acceptable parameters or requires replacement.
        6. **Critical Wavelengths**: Highlight specific IR frequencies showing significant changes that correlate with grease degradation mechanisms.
        7. **Maintenance Recommendations**: Based on the analysis, provide actionable insights for equipment maintenance and grease replacement schedules.
        
        Focus on practical applications for industrial equipment maintenance, bearing lubrication assessment, and predictive maintenance strategies. Interpret results in the context of tribology and lubrication engineering.
        """
        
        # Generate AI analysis with fallback
        try:
            response = model.generate_content([
                prompt,
                {
                    "mime_type": "image/png",
                    "data": graph_b64
                }
            ])
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini AI")
                
            ai_insights = response.text
                
        except Exception as e:
            # Fallback to statistical analysis when AI fails
            ai_insights = f"""**Infrared Grease Analysis - Statistical Summary**

**Baseline vs Sample Comparison:**
- Baseline (Fresh Grease): Mean={stats['baseline_stats']['mean_y']:.3f} ± {stats['baseline_stats']['std_y']:.3f}
- Sample ({sample_name}): Mean={stats['sample_stats']['mean_y']:.3f} ± {stats['sample_stats']['std_y']:.3f}
- Spectral Difference: {stats['differences']['mean_diff']:.3f}

**Oxidation Indicator Analysis:**
The sample shows {"increased absorption" if stats['differences']['mean_diff'] > 0 else "decreased absorption" if stats['differences']['mean_diff'] < 0 else "similar spectral behavior"} compared to fresh grease baseline, with a difference of {abs(stats['differences']['mean_diff']):.3f} absorption units.

**Grease Condition Assessment:**
- Spectral Data Points: Baseline ({stats['baseline_stats']['count']}), Sample ({stats['sample_stats']['count']})
- Spectral Variance: {"Increased spectral complexity" if stats['differences']['std_diff'] > 0 else "Reduced spectral complexity" if stats['differences']['std_diff'] < 0 else "Similar spectral consistency"} suggesting {"potential oxidation or contamination" if stats['differences']['std_diff'] > 0 else "stable grease condition"}
- Absorption Range: Baseline [{stats['baseline_stats']['min_y']:.3f}, {stats['baseline_stats']['max_y']:.3f}], Sample [{stats['sample_stats']['min_y']:.3f}, {stats['sample_stats']['max_y']:.3f}]

**Preliminary Maintenance Recommendations:**
{"⚠️ Elevated spectral changes detected - consider detailed IR analysis for oxidation markers (1700-1750 cm⁻¹) and water contamination (3200-3600 cm⁻¹)" if abs(stats['differences']['mean_diff']) > stats['baseline_stats']['std_y'] else "✓ Spectral changes within normal range - grease condition appears stable"}

**Note:** This statistical analysis provides initial grease assessment. Full AI-powered tribological insights will provide detailed oxidation analysis, contamination detection, and maintenance scheduling when the AI service is available."""
        
        # Prepare response
        try:
            from datetime import datetime
            analysis_result = {
                "sample_name": sample_name,
                "statistics": stats,
                "ai_insights": ai_insights,
                "metadata": {
                    "baseline_file": baseline.filename,
                    "sample_file": sample.filename,
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }
            
            return JSONResponse(content=analysis_result)
        except Exception as e:
            return JSONResponse(
                status_code=500, 
                content={"error": f"Failed to prepare response: {str(e)}"}
            )
        
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to generate insights: {str(e)}"}
        )


def _parse_zone_weights(value: Optional[str]) -> list[dict] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("zone_weights must be valid JSON") from exc
    if not isinstance(parsed, list):
        raise ValueError("zone_weights must be a JSON array")
    return parsed


async def _read_upload(upload: UploadFile) -> bytes:
    return await upload.read()


@router.post("/ftir/deviation")
async def calculate_ftir_deviation(
    baseline: UploadFile = File(...),
    sample: UploadFile = File(...),
    zone_weights: Optional[str] = Form(None),
):
    started = time.perf_counter()
    try:
        weights = _parse_zone_weights(zone_weights)
        baseline_bytes, sample_bytes = await _read_upload(baseline), await _read_upload(sample)
        result = AnalysisService().calculate(
            baseline_bytes, baseline.filename or "baseline", [(sample_bytes, sample.filename or "sample")],
            zone_weights=weights,
        )
        sample_x, _ = AnalysisService._parse(sample_bytes, sample.filename or "sample")
        return {
            "success": True,
            "deviationData": result["deviationData"],
            "sampleInfo": {
                "filename": sample.filename,
                "dataPoints": len(sample_x),
                "wavelengthRange": [float(sample_x.min()), float(sample_x.max())],
            },
            "processingTime": (time.perf_counter() - started) * 1000,
        }
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": str(exc), "details": {}}})


@router.post("/ftir/scores")
async def calculate_ftir_scores(
    baseline: UploadFile = File(...),
    samples: List[UploadFile] = File(...),
    scoring_method: str = Form("hybrid"),
    zone_weights: Optional[str] = Form(None),
):
    started = time.perf_counter()
    try:
        weights = _parse_zone_weights(zone_weights)
        baseline_bytes = await _read_upload(baseline)
        sample_bytes = [(await _read_upload(sample), sample.filename or "sample") for sample in samples]
        result = AnalysisService().calculate(
            baseline_bytes, baseline.filename or "baseline", sample_bytes,
            scoring_method=scoring_method, zone_weights=weights,
        )
        return {
            "success": True,
            **result,
            "processingTime": (time.perf_counter() - started) * 1000,
        }
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": str(exc), "details": {}}})


@router.post("/ftir/sessions/save")
async def save_ftir_session_not_implemented():
    return JSONResponse(
        status_code=501,
        content={"error": "FTIR session save is not implemented yet"},
    )


@router.get("/ftir/sessions/history")
async def get_ftir_session_history_not_implemented():
    return JSONResponse(
        status_code=501,
        content={"error": "FTIR session history is not implemented yet"},
    )


@router.get("/health")
async def analysis_health():
    """Health check for analysis service"""
    gemini_status = "configured" if Settings.from_environment().gemini_api_key else "not_configured"
    return {
        "status": "ok",
        "gemini_api": gemini_status,
        "service": "graph_analysis"
    }
