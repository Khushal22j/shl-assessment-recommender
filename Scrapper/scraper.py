import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin

BASE_URL = "https://www.shl.com/solutions/products/product-catalog/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

all_products = []

def safe_get(url, retries=3, sleep=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                return response
            print(f"Attempt {attempt+1}: Status {response.status_code} for {url}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}: Request failed for {url} - {e}")
        time.sleep(sleep)
    print(f"Failed to fetch {url} after {retries} attempts")
    return None

def normalize_url(href, base_url=BASE_URL):
    if not href:
        return None

    if href.startswith('http'):
        full_url = href
    else:
        full_url = urljoin('https://www.shl.com', href)

    if '/product-catalog/view/' in full_url:
        full_url = full_url.replace('/products/product-catalog/', '/solutions/products/product-catalog/')

    if not full_url.endswith('/'):
        full_url += '/'

    return full_url

def is_browser_warning(text):
    if not text:
        return False

    text_lower = text.lower()
    warning_keywords = [
        'browser', 'upgrade', 'modern browser', 'outdated',
        'cookie', 'privacy', 'experience', 'guarantee',
        'javascript', 'enable', 'disable', 'version'
    ]

    matches = sum(1 for keyword in warning_keywords if keyword in text_lower)
    return matches >= 2

def extract_real_description(soup, product_name):
    description = ""

    product_selectors = [
        'div[data-testid="product-description"]',
        'div.product-description',
        'section.product-info',
        'div.rich-text',
        'article.product-content',
        'div.product-details',
        'div.assessment-description'
    ]

    for selector in product_selectors:
        container = soup.select_one(selector)
        if container:
            paragraphs = container.find_all(['p', 'li', 'div'])
            if paragraphs:
                text_parts = []
                for elem in paragraphs:
                    text = elem.get_text(' ', strip=True)
                    if text and len(text) > 20 and not is_browser_warning(text):
                        text_parts.append(text)
                if text_parts:
                    description = ' '.join(text_parts)
                    if len(description) > 50:
                        return description[:800]

    main_content = soup.find('main') or soup.find('div', role='main') or soup.body

    if main_content:
        all_paragraphs = main_content.find_all(['p', 'div'])
        meaningful_texts = []

        for elem in all_paragraphs:
            text = elem.get_text(' ', strip=True)
            if not text or len(text) < 40:
                continue

            if (
                is_browser_warning(text) or
                'menu' in text.lower() or
                'navigation' in text.lower() or
                'skip to' in text.lower()
            ):
                continue

            product_keywords = [
                'assessment', 'test', 'measure', 'skill', 'ability',
                'candidate', 'evaluate', 'role', 'job', 'position',
                'competency', 'knowledge', 'behavior', 'scenario'
            ]

            if any(keyword in text.lower() for keyword in product_keywords):
                if len(text) > 50:
                    meaningful_texts.append(text)

        if meaningful_texts:
            description = ' '.join(meaningful_texts[:5])
            return description[:800]

    fallback_keywords = ['Solution', 'Test', 'Assessment', 'Simulation']
    for keyword in fallback_keywords:
        if keyword in product_name:
            return f"This {keyword.lower()} evaluates skills and competencies relevant for {product_name.replace(keyword, '').strip()} roles."

    return f"Assessment for {product_name}. Measures relevant skills and competencies."

def extract_test_type(description, product_name):
    text = (description + ' ' + product_name).lower()
    test_types = []

    type_patterns = {
        'K': ['programming', 'java', 'python', 'sql', 'technical', 'code', 'software', 'framework', 'language', 'knowledge', 'skill'],
        'P': ['personality', 'behavior', 'communication', 'interpersonal', 'collaborat', 'teamwork', 'trait', 'psychometric'],
        'A': ['aptitude', 'cognitive', 'numerical', 'verbal', 'logical', 'reasoning', 'ability'],
        'S': ['simulation', 'exercise', 'scenario', 'role-play', 'in-basket'],
        'B': ['situational', 'judgment', 'biodata'],
        'C': ['competency', 'competence']
    }

    for code, keywords in type_patterns.items():
        if any(keyword in text for keyword in keywords):
            test_types.append(code)

    return test_types if test_types else ['K']

def extract_duration(description, product_name):
    text = (description + ' ' + product_name).lower()

    patterns = [
        (r'(\d+)\s*min', 1),
        (r'(\d+)\s*minutes', 1),
        (r'(\d+)\s*hour', 60),
        (r'(\d+)\s*hours', 60),
        (r'(\d+)\s*hr', 60),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1)) * multiplier
            except ValueError:
                pass

    if any(word in text for word in ['simulation', 'exercise', 'scenario']):
        return 60
    if any(word in text for word in ['personality', 'behavior', 'cognitive']):
        return 30

    return 30

def scrape_product_page(product_url):
    print(f"Scraping: {product_url}")
    response = safe_get(product_url)
    if not response:
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    name = ""
    title_tag = soup.find('h1')
    if title_tag:
        name = title_tag.get_text(strip=True)

    if not name:
        title_tag = soup.find('title')
        if title_tag:
            name = title_tag.get_text(strip=True).split('|')[0].strip()
        else:
            name = "Unnamed Assessment"

    description = extract_real_description(soup, name)
    test_type = extract_test_type(description, name)
    duration = extract_duration(description, name)

    full_text = (name + ' ' + description).lower()
    adaptive = 'Yes' if 'adaptive' in full_text else 'No'
    remote = 'Yes'

    return {
        'name': name,
        'url': product_url,
        'description': description,
        'test_type': test_type,
        'duration': duration,
        'adaptive_support': adaptive,
        'remote_support': remote
    }

def scrape_catalog():
    global all_products
    seen_urls = set()
    offset = 0
    page_size = 12
    max_empty = 3
    empty_count = 0

    while True:
        catalog_url = f"{BASE_URL}?type=1&start={offset}"
        response = safe_get(catalog_url)

        if not response:
            empty_count += 1
            if empty_count >= max_empty:
                break
            offset += page_size
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        product_links = set()

        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/product-catalog/view/' in href:
                normalized_url = normalize_url(href)
                if normalized_url and '/solution/' not in normalized_url.lower():
                    product_links.add(normalized_url)

        if not product_links:
            empty_count += 1
            if empty_count >= max_empty:
                break
        else:
            empty_count = 0

        new_links = [url for url in product_links if url not in seen_urls]

        for product_url in new_links:
            product_data = scrape_product_page(product_url)
            if product_data:
                if is_browser_warning(product_data['description']):
                    product_data['description'] = extract_real_description(
                        BeautifulSoup("<html></html>", 'html.parser'),
                        product_data['name']
                    )
                all_products.append(product_data)
                seen_urls.add(product_url)
            time.sleep(0.7)

        if len(all_products) >= 377:
            break

        offset += page_size

    with open('shl_data_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)

    return all_products

def test_specific_urls():
    test_urls = [
        'https://www.shl.com/solutions/products/product-catalog/view/account-manager-solution/',
        'https://www.shl.com/solutions/products/product-catalog/view/java-8-new/',
        'https://www.shl.com/solutions/products/product-catalog/view/interpersonal-communications/'
    ]

    for url in test_urls:
        data = scrape_product_page(url)
        time.sleep(1)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_specific_urls()
    else:
        start_time = time.time()
        try:
            all_products = scrape_catalog()
            elapsed = time.time() - start_time
            print(f"Total time: {elapsed:.2f} seconds")
        except KeyboardInterrupt:
            if all_products:
                with open('shl_data_partial.json', 'w', encoding='utf-8') as f:
                    json.dump(all_products, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Unexpected error: {e}")
