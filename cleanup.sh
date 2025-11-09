#!/bin/bash

# Cleanup script to reset the application for fresh start
# TAMU Datathon - Document Classifier

echo "🧹 Cleaning up AI Document Classifier..."
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

# Clean results directory (keep .gitkeep)
echo "📁 Cleaning results directory..."
find results -type f ! -name '.gitkeep' -delete
if [ -d "results/feedback" ]; then
    find results/feedback -type f ! -name '.gitkeep' -delete
fi

# Clean uploads directory (keep .gitkeep)
echo "📁 Cleaning uploads directory..."
find uploads -type f ! -name '.gitkeep' -delete

# Count what was cleaned
echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Directories reset:"
echo "  - results/          (classification results cleared)"
echo "  - results/feedback/ (HITL feedback cleared)"
echo "  - uploads/          (uploaded files cleared)"
echo ""
echo "🔄 Ready for fresh start!"
echo ""
echo "To restart servers:"
echo "  Backend:  cd backend && python3 -m uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
