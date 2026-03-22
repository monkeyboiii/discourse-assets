# Sources

## Emojis

1. [data.js](https://github.com/discourse/discourse/blob/main/frontend/pretty-text/addon/emoji/data.js) is the emoji canonical names, aliases, toning, mappings etc.
2. [emojis.json](https://meta.discourse.org/emojis.json) is the API result from site.
3. [ios-emojis-by-line.txt](./ios-emojis-by-line.txt) is my attempt to separate ios line by line.

## Icons
1. [sprite-meta.xml](https://meta.discourse.org/svg-sprite/meta.discourse.org/svg-331-65535d75fc984156c33bf043d0a3bf3e47547b54.js) is loaded in first into `window.__svg_sprite`. Retrievable from  site `Doc` in chrome inspector (F12) `meta` "data-discourse-setup" tag. The path is subject to change.

```html
<meta id="data-discourse-setup"
    data-cdn="https://d3bpeqsaub0i6y.cloudfront.net"
    data-base-url="https://meta.discourse.org" 
    data-base-uri="" 
    data-environment="production"
    data-letter-avatar-version="5_c16b2ee14fe83ed9a59fc65fbec00f85" 
    data-service-worker-url="service-worker.js"
    data-default-locale="en" 
    data-asset-version="1f8c6425122e54f7bae8f7a14199f293" 
    data-disable-custom-css="false"
    data-highlight-js-path="/highlight-js/meta.discourse.org/600885de53a0c5dcaf15540b83e94aafa44c5313.js"
    data-svg-sprite-path="/svg-sprite/meta.discourse.org/svg-331-65535d75fc984156c33bf043d0a3bf3e47547b54.js"
    data-media-optimization-bundle="https://d11a6trkgmumsb.cloudfront.net/assets/chunk.c3f5f9efba854a48230e.d41d8cd9.br.js"
    data-color-scheme-is-dark="false" 
    data-user-color-scheme-id="34" 
    data-user-dark-scheme-id="111"
    data-s3-cdn="https://d11a6trkgmumsb.cloudfront.net"
    data-s3-base-url="//assets-meta-cdck-prod-meta.s3.dualstack.us-west-1.amazonaws.com">
```

2. [sprite-dbc.xml](./sprite-dbc.xml) site specific, to [forum.dirtbikechina.com](https://forum.dirtbikechina.com/).