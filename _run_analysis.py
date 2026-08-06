"""Run PMO analysis for today's (7/24) data"""
import sys, os, glob
os.chdir(r'C:\Users\zhahuang\Documents\Customer-Data\国电投\开发任务管理')
sys.path.insert(0, 'pmo-analysis-skill/scripts')

# Find today's data file
files = glob.glob('data/*2026_7_24*.xlsx')
if not files:
    print('ERROR: No 7/24 data file found!')
    sys.exit(1)
input_file = files[0]
print(f'Found: {input_file}')

sys.argv = ['pmo_analyzer.py', input_file]
from pmo_analyzer import main
main()
