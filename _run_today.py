import sys, os, glob
os.chdir(r'C:\Users\zhahuang\Documents\Customer-Data\国电投\开发任务管理')
sys.path.insert(0, r'.qoder\skills\pmo-analysis-skill\scripts')
files = sorted([f for f in glob.glob('data/*2026_7_26*.xlsx') if not os.path.basename(f).startswith('~$')])
sys.argv = ['pmo_analyzer.py', files[0]]
from pmo_analyzer import main
main()
