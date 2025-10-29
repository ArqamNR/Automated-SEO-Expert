import re
query = "SELECT  SUM(pm.impressions) FROM  pages pJOIN performance_metrics pm  ON  p.id = pm.page_idWHERE p.url = 'https://theplantsmall.com/';"
keywords = [
                'SELECT', 'FROM', 'JOIN', 'ON', 'WHERE', 'ORDER BY', 'GROUP BY',
                'LIMIT', 'DESC', 'ASC'
            ]
pattern = r'([a-zA-Z0-9])(JOIN|FROM|WHERE|ORDER BY|GROUP BY|LIMIT|DESC|ASC)'
corrected_query = re.sub(pattern, r'\1 \2', query, flags=re.IGNORECASE)
corrected_query = re.sub(r'\s+', ' ', corrected_query).strip()
print(corrected_query)