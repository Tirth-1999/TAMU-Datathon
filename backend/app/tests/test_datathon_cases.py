"""
Datathon Test Case Validation Suite
Tests against the 5 official test cases (TC1-TC5)
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.document_processor import DocumentProcessor
from app.services.classifier import DocumentClassifier
import os


class TestCaseValidator:
    """Validates classification against Datathon test cases"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.classifier = DocumentClassifier(api_key=api_key)
        
        # Define test cases with expected outcomes
        self.test_cases = {
            "TC1": {
                "filename": "TC1_Sample_Public_Marketing_Document.pdf",
                "expected_classification": "Public",
                "expected_features": {
                    "has_pii": False,
                    "is_safe": True,
                    "min_confidence": 0.85,
                    "should_have_evidence": True,
                    "should_cite_pages": True
                },
                "description": "Public marketing document - should be clearly Public with high confidence"
            },
            "TC2": {
                "filename": "TC2_Filled_In_Employement_Application.pdf",
                "expected_classification": "Highly Sensitive",
                "expected_features": {
                    "has_pii": True,
                    "contains_ssn": True,
                    "is_safe": True,
                    "min_confidence": 0.90,
                    "requires_review": False,  # Should be confident about PII
                    "should_have_evidence": True
                },
                "description": "Employment application with PII including SSN - must be Highly Sensitive"
            },
            "TC3": {
                "filename": "TC3_Sample_Internal_Memo.pdf",
                "expected_classification": "Confidential",
                "expected_features": {
                    "has_pii": False,
                    "is_safe": True,
                    "min_confidence": 0.75,
                    "should_have_evidence": True
                },
                "description": "Internal memo without PII - should be Confidential"
            },
            "TC4": {
                "filename": "TC4_Stealth_Fighter_With_Part_Names.pdf",
                "expected_classification": ["Confidential", "Highly Sensitive"],  # Either is acceptable
                "expected_features": {
                    "has_defense_content": True,
                    "has_technical_specs": True,
                    "is_safe": True,
                    "min_confidence": 0.70,
                    "should_cite_part_names": True,
                    "should_have_evidence": True
                },
                "description": "Stealth fighter with part names - Confidential or Highly Sensitive"
            },
            "TC5": {
                "filename": "TC5_Testing_Multiple_Non_Compliance_Categorization.docx",
                "expected_classification": "Unsafe",  # Primary should be Unsafe
                "expected_features": {
                    "is_safe": False,
                    "has_multiple_violations": True,
                    "should_have_safety_flags": True,
                    "min_confidence": 0.75,
                    "additional_labels_expected": True  # Should have Confidential or other labels too
                },
                "description": "Multiple violations - must detect Unsafe + other categories"
            }
        }
    
    async def run_test_case(self, test_id: str, test_path: Path) -> Dict[str, Any]:
        """Run a single test case"""
        test_config = self.test_cases.get(test_id)
        if not test_config:
            return {"error": f"Unknown test case: {test_id}"}
        
        print(f"\n{'='*80}")
        print(f"Testing {test_id}: {test_config['description']}")
        print(f"File: {test_config['filename']}")
        print(f"{'='*80}\n")
        
        # Check if file exists
        if not test_path.exists():
            return {
                "test_id": test_id,
                "status": "SKIP",
                "reason": f"File not found: {test_path}"
            }
        
        try:
            # Process document
            print(f"[1/4] Processing document...")
            content_blocks, metadata = self.processor.process_file(test_path)
            
            print(f"[2/4] Document processed:")
            print(f"  - Pages: {metadata.page_count}")
            print(f"  - Images: {metadata.image_count}")
            print(f"  - Format: {metadata.format}")
            
            # Classify
            print(f"[3/4] Running classification...")
            result = self.classifier.classify_document(
                content_blocks=content_blocks,
                metadata=metadata,
                document_id=f"test_{test_id}",
                enable_dual_verification=False
            )
            
            print(f"[4/4] Classification complete!")
            print(f"  - Classification: {result.classification}")
            print(f"  - Confidence: {result.confidence:.2f}")
            print(f"  - Safety: {'✅ Safe' if result.safety_check.is_safe else '⚠️ Unsafe'}")
            print(f"  - Evidence count: {len(result.evidence)}")
            
            # Validate against expected outcomes
            validation = self._validate_result(test_id, result, test_config)
            
            return {
                "test_id": test_id,
                "status": "PASS" if validation["passed"] else "FAIL",
                "result": {
                    "classification": result.classification,
                    "confidence": result.confidence,
                    "safety": result.safety_check.is_safe,
                    "evidence_count": len(result.evidence),
                    "requires_review": result.requires_review,
                    "review_reason": result.review_reason,
                    "additional_labels": result.additional_labels if hasattr(result, 'additional_labels') else []
                },
                "validation": validation,
                "test_config": test_config
            }
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {
                "test_id": test_id,
                "status": "ERROR",
                "error": str(e),
                "test_config": test_config
            }
    
    def _validate_result(
        self,
        test_id: str,
        result: Any,
        test_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate classification result against expected outcomes"""
        
        validation = {
            "passed": True,
            "checks": [],
            "warnings": [],
            "failures": []
        }
        
        expected_class = test_config["expected_classification"]
        expected_features = test_config["expected_features"]
        
        # Check 1: Classification matches
        if isinstance(expected_class, list):
            if result.classification not in expected_class:
                validation["passed"] = False
                validation["failures"].append(
                    f"Classification '{result.classification}' not in expected {expected_class}"
                )
            else:
                validation["checks"].append(
                    f"✅ Classification '{result.classification}' matches expected"
                )
        else:
            if result.classification != expected_class:
                validation["passed"] = False
                validation["failures"].append(
                    f"Expected '{expected_class}', got '{result.classification}'"
                )
            else:
                validation["checks"].append(
                    f"✅ Classification matches: {expected_class}"
                )
        
        # Check 2: Confidence threshold
        min_confidence = expected_features.get("min_confidence", 0.70)
        if result.confidence < min_confidence:
            validation["warnings"].append(
                f"⚠️ Confidence {result.confidence:.2f} below threshold {min_confidence}"
            )
        else:
            validation["checks"].append(
                f"✅ Confidence {result.confidence:.2f} meets threshold"
            )
        
        # Check 3: Safety assessment
        expected_safe = expected_features.get("is_safe", True)
        if result.safety_check.is_safe != expected_safe:
            validation["passed"] = False
            validation["failures"].append(
                f"Expected is_safe={expected_safe}, got {result.safety_check.is_safe}"
            )
        else:
            validation["checks"].append(
                f"✅ Safety check: {'Safe' if expected_safe else 'Unsafe'}"
            )
        
        # Check 4: Evidence with page citations
        if expected_features.get("should_have_evidence", False):
            if len(result.evidence) == 0:
                validation["passed"] = False
                validation["failures"].append("No evidence provided")
            else:
                validation["checks"].append(
                    f"✅ Evidence provided: {len(result.evidence)} items"
                )
            
            if expected_features.get("should_cite_pages", False):
                has_page_citations = any(e.page > 0 for e in result.evidence)
                if not has_page_citations:
                    validation["warnings"].append(
                        "⚠️ Evidence does not cite specific pages"
                    )
                else:
                    validation["checks"].append(
                        "✅ Evidence includes page citations"
                    )
        
        # Check 5: PII detection (for TC2)
        if test_id == "TC2" and expected_features.get("contains_ssn", False):
            evidence_text = " ".join(e.quote for e in result.evidence).lower()
            if "ssn" not in evidence_text and "social security" not in evidence_text:
                validation["warnings"].append(
                    "⚠️ Evidence does not explicitly mention SSN"
                )
            else:
                validation["checks"].append(
                    "✅ Evidence mentions PII/SSN"
                )
        
        # Check 6: Defense content (for TC4)
        if test_id == "TC4" and expected_features.get("has_defense_content", False):
            evidence_text = " ".join(e.quote for e in result.evidence).lower()
            defense_keywords = ['fighter', 'aircraft', 'part', 'component']
            found_keywords = [kw for kw in defense_keywords if kw in evidence_text]
            
            if not found_keywords:
                validation["warnings"].append(
                    "⚠️ Evidence does not mention defense/fighter keywords"
                )
            else:
                validation["checks"].append(
                    f"✅ Evidence mentions defense keywords: {found_keywords}"
                )
        
        # Check 7: Multiple violations (for TC5)
        if test_id == "TC5":
            if not expected_features.get("should_have_safety_flags", False):
                validation["warnings"].append(
                    "⚠️ Expected safety flags for multiple violations"
                )
            else:
                if len(result.safety_check.flags) > 1:
                    validation["checks"].append(
                        f"✅ Multiple safety flags: {result.safety_check.flags}"
                    )
                else:
                    validation["warnings"].append(
                        f"⚠️ Only {len(result.safety_check.flags)} safety flag(s)"
                    )
        
        # Check 8: Page count validation
        if result.page_count == 0:
            validation["warnings"].append(
                "⚠️ Page count is 0 - document may not have been processed correctly"
            )
        
        return validation
    
    async def run_all_tests(self, test_dir: Path) -> Dict[str, Any]:
        """Run all test cases"""
        
        print(f"\n{'#'*80}")
        print(f"# DATATHON TEST CASE VALIDATION SUITE")
        print(f"# Testing against official test cases TC1-TC5")
        print(f"# Test directory: {test_dir}")
        print(f"{'#'*80}\n")
        
        results = []
        
        for test_id in ["TC1", "TC2", "TC3", "TC4", "TC5"]:
            test_config = self.test_cases[test_id]
            test_path = test_dir / test_config["filename"]
            
            result = await self.run_test_case(test_id, test_path)
            results.append(result)
            
            # Print summary
            status = result["status"]
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "SKIP": "⏭️",
                "ERROR": "💥"
            }.get(status, "❓")
            
            print(f"\n{status_icon} {test_id}: {status}")
            
            if result.get("validation"):
                val = result["validation"]
                if val.get("failures"):
                    for failure in val["failures"]:
                        print(f"  ❌ {failure}")
                if val.get("warnings"):
                    for warning in val["warnings"]:
                        print(f"  {warning}")
            
            print()
        
        # Summary
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        skipped = sum(1 for r in results if r["status"] == "SKIP")
        errors = sum(1 for r in results if r["status"] == "ERROR")
        
        print(f"\n{'='*80}")
        print(f"SUMMARY:")
        print(f"  ✅ Passed: {passed}/5")
        print(f"  ❌ Failed: {failed}/5")
        print(f"  ⏭️  Skipped: {skipped}/5")
        print(f"  💥 Errors: {errors}/5")
        print(f"{'='*80}\n")
        
        return {
            "summary": {
                "total": 5,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "success_rate": f"{(passed / 5) * 100:.1f}%"
            },
            "results": results
        }


async def main():
    """Main test runner"""
    import sys
    
    # Get test directory from command line or use default
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        test_dir = Path(__file__).parent.parent.parent / "test_cases"
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        print(f"\nUsage: python test_datathon_cases.py [test_directory]")
        print(f"\nExpected test files:")
        validator = TestCaseValidator()
        for test_id, config in validator.test_cases.items():
            print(f"  - {config['filename']}")
        return
    
    # Run tests
    validator = TestCaseValidator()
    results = await validator.run_all_tests(test_dir)
    
    # Save results to file
    results_file = Path(__file__).parent / "test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📄 Full results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
