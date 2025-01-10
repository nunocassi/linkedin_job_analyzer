import os
from datetime import datetime
from job_analyzer import LinkedInJobAnalyzer

def create_output_directory():
    """Cria uma pasta de outputs com timestamp"""
    # Cria pasta 'outputs' se não existir
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    
    # Cria subpasta com timestamp atual
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join('outputs', timestamp)
    os.makedirs(output_dir)
    
    return output_dir

def main():
    try:
        # Cria diretório para outputs
        output_dir = create_output_directory()
        print(f"Outputs serão salvos em: {output_dir}")
        
        # Inicializa o analisador
        print("Iniciando o analisador...")
        analyzer = LinkedInJobAnalyzer()
        
        # Busca vagas
        print("Buscando vagas...")
        df = analyzer.search_jobs(keyword="python developer", location="Lisboa", num_pages=1)
        
        print(f"\nEncontradas {len(df)} vagas")
        print("\nPrimeiras linhas dos dados:")
        print(df.head())
        
        # Salva o DataFrame em CSV
        csv_path = os.path.join(output_dir, 'jobs_data.csv')
        df.to_csv(csv_path, index=False)
        print(f"\nDados salvos em: {csv_path}")
        
        # Realiza análises
        print("\nRealizando análises...")
        analyses = analyzer.analyze_data(df)
        
        # Cria visualizações
        print("\nGerando visualizações...")
        visualizations = analyzer.create_visualizations(analyses)
        
        # Salva as visualizações
        for name, fig in visualizations.items():
            viz_path = os.path.join(output_dir, f'visualization_{name}.html')
            fig.write_html(viz_path)
            print(f"Visualização '{name}' salva em: {viz_path}")
        
        print("\nProcesso concluído com sucesso!")
        print(f"Todos os outputs foram salvos em: {output_dir}")
        
    except Exception as e:
        print(f"\nErro durante a execução: {str(e)}")

if __name__ == "__main__":
    main()