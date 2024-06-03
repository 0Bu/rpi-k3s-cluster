# [Home Assistant](https://www.home-assistant.io)
- [GitHub](https://github.com/home-assistant/core)
- [Docker](https://hub.docker.com/r/homeassistant/home-assistant)

## Helm install/upgrade
`helm upgrade --install home-assistant .`

## Helm unintall
`helm uninstall home-assistant`

## Reverse proxy configuration
configuration.yaml

```
http:
  use_x_forwarded_for: true # https://www.home-assistant.io/integrations/http#use_x_forwarded_for
  trusted_proxies:          # https://www.home-assistant.io/integrations/http#trusted_proxies
    - 10.0.0.0/8 # 
```
