import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import re


class LinkedInJobAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,pt-PT;q=0.8,pt;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        self.base_url = 'https://www.linkedin.com/jobs/search'
        self.jobs_data = []

    def search_jobs(self, keyword, location='Portugal', num_pages=10):
        """
        Busca vagas no LinkedIn baseado na palavra-chave e localização
        """
        # Format location to ensure proper search
        formatted_location = f"{location}, Portugal" if "Portugal" not in location else location
        
        for page in range(num_pages):
            try:
                params = {
                    'keywords': keyword,
                    'location': formatted_location,
                    'start': page * 25,
                    'geoId': '100364837',  # LinkedIn's geoId for Portugal
                    'countryCode': 'pt',    # Country code for Portugal
                }

                response = requests.get(self.base_url, headers=self.headers, params=params)
                if response.status_code == 200:
                    self._parse_jobs_page(response.content)
                else:
                    print(f"Error: Status code {response.status_code}")
                    print(f"Response: {response.text[:500]}")  # Print first 500 chars of response

                time.sleep(2)  # Pause to avoid blocking

            except Exception as e:
                print(f"Error fetching page {page}: {str(e)}")

        return self._create_dataframe()

    def _parse_jobs_page(self, html_content):
        """
        Extrai informações das vagas da página HTML com melhor tratamento para descrições
        e filtra por vagas das últimas 24 horas
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        jobs_list = soup.find_all('div', class_='job-search-card')

        for job in jobs_list:
            try:
                job_link = job.find('a')
                if job_link and 'href' in job_link.attrs:
                    job_url = job_link['href']
                    # Clean up the URL if needed
                    if '?' in job_url:
                        job_url = job_url.split('?')[0]
                        
                    description = self._get_job_description(job_url)
                    
                    posted_date = job.find('time')['datetime'] if job.find('time') else None
                    
                    # Check if job was posted in the last 24 hours
                    if posted_date:
                        posted_datetime = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                        time_difference = datetime.now(posted_datetime.tzinfo) - posted_datetime
                        
                        if time_difference.total_seconds() <= 24 * 3600:  # 24 hours in seconds
                            job_data = {
                                'title': job.find('h3', class_='base-search-card__title').text.strip(),
                                'company': job.find('h4', class_='base-search-card__subtitle').text.strip(),
                                'location': job.find('span', class_='job-search-card__location').text.strip(),
                                'posted_date': posted_date,
                                'job_url': job_url,  # Adding the job URL for reference
                                'description': description,
                                'hours_ago': round(time_difference.total_seconds() / 3600, 1)  # Added hours ago
                            }
                            self.jobs_data.append(job_data)
                            print(f"Found job posted {round(time_difference.total_seconds() / 3600, 1)} hours ago: {job_data['title']}")
                    
                    # Add a small delay between requests to avoid rate limiting
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error extracting job data: {str(e)}")
                continue

    def _get_job_description(self, job_url):
        """
        Obtém a descrição completa da vaga, incluindo conteúdo expandido
        """
        try:
            response = requests.get(job_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try different possible selectors for job description
                description_selectors = [
                    'div.show-more-less-html__markup',  # Main description container
                    'div.description__text',            # Alternative description container
                    'div.job-description',              # Another possible container
                ]
                
                description_text = []
                
                for selector in description_selectors:
                    description_elements = soup.select(selector)
                    if description_elements:
                        for element in description_elements:
                            # Remove "show more" and "see more" buttons
                            for button in element.select('.show-more-less-button, .show-more-button'):
                                button.decompose()
                                
                            # Get the text and clean it up
                            text = element.get_text(separator='\n', strip=True)
                            description_text.append(text)
                
                if description_text:
                    # Join all found description parts and clean up the text
                    full_description = '\n'.join(description_text)
                    
                    # Clean up extra whitespace and common artifacts
                    full_description = re.sub(r'\s+', ' ', full_description)  # Replace multiple spaces
                    full_description = re.sub(r'(Show\s*more|See\s*more|Show\s*less)', '', full_description, flags=re.IGNORECASE)
                    full_description = re.sub(r'\s*\.\s*\.\s*\.\s*', '... ', full_description)  # Clean up ellipsis
                    
                    # Remove any remaining UI artifacts
                    full_description = re.sub(r'(\+|\s+Show\s+more\s+Show\s+less\s+)', '', full_description)
                    
                    return full_description.strip()
                    
                return "No description available"
                
        except Exception as e:
            print(f"Error fetching job description: {str(e)}")
            return None

    def _create_dataframe(self):
        """
        Cria um DataFrame com os dados coletados
        """
        df = pd.DataFrame(self.jobs_data)
        df['posted_date'] = pd.to_datetime(df['posted_date'])
        return df

    def analyze_data(self, df):
        """
        Realiza análises nos dados coletados
        """
        analyses = {
            'total_jobs': len(df),
            'top_companies': df['company'].value_counts().head(10),
            'locations_distribution': df['location'].value_counts().head(10),
            'common_skills': self._extract_skills(df),
            'posting_trends': df['posted_date'].dt.date.value_counts().sort_index()
        }
        return analyses

    def _extract_skills(self, df):
        """
        Extrai habilidades mencionadas nas descrições das vagas
        """
        common_skills = ['python', 'java', 'sql', 'aws', 'azure', 'javascript',
                        'react', 'node', 'docker', 'kubernetes', 'agile', 'scrum']

        skill_counts = {}
        for skill in common_skills:
            mask = df['description'].str.contains(skill, case=False, na=False)
            skill_counts[skill] = mask.sum()

        return pd.Series(skill_counts).sort_values(ascending=False)

    def create_visualizations(self, analyses):
        """
        Cria visualizações dos dados analisados
        """
        # Gráfico de barras para empresas
        fig_companies = px.bar(
            analyses['top_companies'],
            title='Top Empresas Contratando',
            labels={'value': 'Número de Vagas', 'index': 'Empresa'}
        )

        # Gráfico de pizza para localidades
        fig_locations = px.pie(
            values=analyses['locations_distribution'],
            names=analyses['locations_distribution'].index,
            title='Distribuição de Vagas por Localidade'
        )

        # Gráfico de barras para skills
        fig_skills = px.bar(
            analyses['common_skills'],
            title='Habilidades Mais Requisitadas',
            labels={'value': 'Número de Menções', 'index': 'Habilidade'}
        )

        # Gráfico de linha para tendências temporais
        fig_trends = px.line(
            analyses['posting_trends'],
            title='Tendência de Publicação de Vagas',
            labels={'index': 'Data', 'value': 'Número de Vagas'}
        )

        return {
            'companies': fig_companies,
            'locations': fig_locations,
            'skills': fig_skills,
            'trends': fig_trends
        }
