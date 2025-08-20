# AI-Powered SaaS Repricing Platform

A production-grade Django SaaS platform that provides AI-powered repricing engines, conditional repricing strategies, and comprehensive market analysis tools for Amazon and Flipkart marketplaces.

## 🚀 Features

### Core Functionality
- **AI-Powered Repricing Engine**: Rule-based + algorithmic/ML strategies
- **Conditional/Contextual Repricing**: Auto-switch strategies by market context
- **Market Analysis Tools**: Competitor tracking, category insights, keyword trends
- **Multi-Tenant SaaS**: Full organization management with billing and permissions
- **Marketplace Integrations**: Amazon SP-API and Flipkart Marketplace API

### Technical Highlights
- **Django 5.x** with server-side rendering
- **PostgreSQL** primary database with Redis caching
- **Celery** for asynchronous task processing
- **Multi-tenancy** with organization-based data isolation
- **RBAC** (Role-Based Access Control)
- **Stripe Integration** for billing and subscriptions
- **Comprehensive Audit Logging** for compliance
- **Docker** containerization with Kubernetes manifests
- **Security** OWASP ASVS-aware patterns, CSRF protection, CSP headers

## 🏗️ Architecture

### Django Apps Structure

```
repricing_platform/
├── accounts/          # User management & multi-tenancy
├── analytics/         # Market analysis & dashboards
├── audit/            # Audit logging & compliance
├── billing/          # Stripe billing & subscriptions
├── catalog/          # Product & listing management
├── core/             # Base models & utilities
├── credentials/      # Encrypted API credential storage
├── integrations/     # Marketplace API clients
├── notifications/    # Alert system
├── pricing_ml/       # Machine learning models
├── pricing_rules/    # Rule-based pricing strategies
├── repricer/         # Repricing orchestration
├── web/             # SSR views & templates
└── adminpanel/      # Staff tools
```

### Key Models

- **User & Organization**: Multi-tenant user management
- **Products & Listings**: Catalog management across marketplaces
- **Pricing Strategies**: Rule-based and ML-driven pricing
- **Integrations**: Marketplace API connections
- **Subscriptions**: Stripe billing integration
- **Audit Logs**: Comprehensive activity tracking

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, Django 5.x
- **Database**: PostgreSQL 15+ (primary), Redis 7+ (cache/queue)
- **Task Queue**: Celery with Redis broker
- **Frontend**: Server-side rendering with Django templates
- **Enhancement**: Unpoly for progressive enhancement
- **Styling**: Bootstrap 5
- **Authentication**: django-allauth with SSO support
- **API**: Django REST Framework (internal APIs only)
- **Monitoring**: Sentry, Prometheus metrics
- **Deployment**: Docker, Kubernetes

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Poetry (dependency management)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd repricing-platform
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Web Application: http://localhost:8000
   - Celery Flower (monitoring): http://localhost:5555
   - Mailhog (email testing): http://localhost:8025
   - MinIO (object storage): http://localhost:9001

4. **Default Credentials**
   - Admin: `admin@repricing.local` / `admin123`
   - Demo User: `demo@repricing.local` / `demo123`

### Manual Setup (Development)

1. **Install dependencies**
   ```bash
   poetry install
   poetry shell
   ```

2. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Database setup**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   python manage.py loaddata fixtures/demo_data.json
   python manage.py createsuperuser
   ```

4. **Run development server**
   ```bash
   python manage.py runserver
   ```

5. **Start Celery workers** (separate terminal)
   ```bash
   celery -A repricing_platform worker --loglevel=info
   celery -A repricing_platform beat --loglevel=info
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/repricing_platform
REDIS_URL=redis://localhost:6379/0

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe (use test keys for development)
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AWS (for production file storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name

# Marketplace APIs (sandbox for development)
AMAZON_SP_API_CLIENT_ID=your-client-id
AMAZON_SP_API_CLIENT_SECRET=your-client-secret
FLIPKART_API_KEY=your-api-key
FLIPKART_API_SECRET=your-api-secret

# Monitoring
SENTRY_DSN=your-sentry-dsn
```

### Marketplace API Setup

#### Amazon SP-API
1. Register as an Amazon developer
2. Create a SP-API application
3. Get client ID and secret
4. Configure in `credentials` app

#### Flipkart Marketplace API
1. Register as a Flipkart seller
2. Apply for API access
3. Get API credentials
4. Configure in `credentials` app

## 📊 Key Features Deep Dive

### AI-Powered Repricing Engine

The platform supports multiple repricing strategies:

1. **Rule-Based Strategies**
   - Undercut by amount/percentage
   - Match buy box price
   - Ignore low-rating competitors
   - Min/max price floors/ceilings
   - ROI floor protection

2. **ML-Based Strategies**
   - Price elasticity estimation
   - Demand forecasting
   - Buy box probability optimization

3. **Conditional Repricing**
   - Auto-switch based on inventory aging
   - Sales velocity adjustments
   - Time-of-day repricing (dayparting)
   - Competitor density response
   - Ad spend/ACOS thresholds

### Safety Guardrails

- Never price below cost + fees + target margin
- Competitor blacklists/whitelists
- Fulfillment-aware filters (FBA/FBM)
- Human-in-the-loop approvals for protected SKUs
- Rollback capabilities

### Market Analysis Tools

- **Competitive Intelligence**: Competitor tracking, price history
- **Category Insights**: Demand trends, opportunity scoring
- **Keyword Analysis**: Rank tracking, brand analytics
- **Profitability Analytics**: Revenue, costs, margins

## 🔐 Security & Compliance

### Security Features
- CSRF protection on all forms
- Secure session settings
- CSP headers implementation
- HSTS in production
- Rate limiting
- Encrypted credential storage
- API credential vaulting

### GDPR Compliance
- Data export functionality
- Right to erasure implementation
- Audit trails for all data access
- Minimal PII storage
- Cookie consent management

### Audit Logging
- Comprehensive activity tracking
- Change history for critical data
- Security event monitoring
- Compliance reporting

## 🚢 Deployment

### Production Deployment

1. **Build Docker image**
   ```bash
   docker build -t repricing-platform:latest .
   ```

2. **Deploy with Kubernetes**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Configure environment variables**
   ```bash
   kubectl create secret generic app-secrets --from-env-file=.env.prod
   ```

### Kubernetes Manifests

The platform includes complete Kubernetes manifests:
- Deployments for web, workers, and beat scheduler
- Services and Ingress configuration
- HPA (Horizontal Pod Autoscaler)
- ConfigMaps and Secrets
- CronJobs for maintenance tasks

### CI/CD Pipeline

GitHub Actions workflow includes:
- Code quality checks (Black, Ruff, isort, MyPy)
- Security scanning (Bandit, Trivy)
- Test execution with coverage
- Docker image building
- Kubernetes deployment

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=repricing_platform --cov-report=html

# Run specific test module
pytest accounts/tests/

# Run integration tests
pytest tests/integration/

# Run E2E tests (requires running application)
playwright test
```

### Test Structure

- **Unit Tests**: 90%+ coverage for domain logic
- **Integration Tests**: API client wrappers with VCR.py
- **E2E Tests**: Critical UI flows with Playwright
- **Property-Based Tests**: Pricing rules correctness with Hypothesis
- **Load Tests**: Repricing job throughput with Locust

## 📚 API Documentation

Internal API documentation is available at:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI Schema: `/api/schema/`

## 🔧 Development Tools

### Code Quality

```bash
# Format code
black .
isort .

# Lint code
ruff check .

# Type checking
mypy .

# Security check
bandit -r repricing_platform/
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## 📈 Monitoring & Observability

### Health Checks
- Liveness probe: `/health/live/`
- Readiness probe: `/health/ready/`

### Metrics
- Prometheus metrics: `/metrics/`
- Custom business metrics
- Performance monitoring

### Logging
- Structured JSON logging
- Centralized log aggregation
- Security event logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines

- Follow Django best practices
- Maintain test coverage above 90%
- Use type hints throughout
- Document all public APIs
- Follow security guidelines

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

- **Documentation**: Check the `/docs/` directory
- **Issues**: Use GitHub Issues for bug reports
- **Questions**: Contact the development team
- **Security Issues**: Report privately to security@repricing.local

## 🗺️ Roadmap

### Current Version (v1.0)
- ✅ Basic repricing engine
- ✅ Amazon SP-API integration
- ✅ Multi-tenant architecture
- ✅ Stripe billing integration

### Upcoming Features (v1.1)
- 🔄 Flipkart API integration
- 🔄 Advanced ML models
- 🔄 Mobile app
- 🔄 Advanced analytics

### Future Versions
- 📋 Additional marketplace integrations
- 📋 Advanced forecasting models
- 📋 Multi-language support
- 📋 API rate optimization

---

**Built with ❤️ using Django and modern web technologies**
