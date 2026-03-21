import sys
sys.path.insert(0, r'd:\mahmoud priv\For Mahmood\TelegramBot_V1')
from data import index_data, smart_search

indexed = index_data()
print(f'Indexed {len(indexed)} sites')

# Find particl in indexed data  
found = [i for i in indexed if 'particl' in i['website'].lower()]
print(f'Found in indexed: {len(found)}')
for f in found:
    w = f['website']
    st = f['search_text'][:80]
    print(f'  website: {w}')
    print(f'  search_text: {st}')

# Test search
results = smart_search('particl', indexed)
print(f'\nSearch results: {len(results)}')
for r in results:
    print(f'  {r["website"]} (score: {r["score"]})')
