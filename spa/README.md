# SPA

## Development

### Setting up your development environment

From the parent directory (ie `/` not `/spa`) run,

```bash
docker compose watch
```

This will tell Docker to start and watch for changes to the SPA app's build directory.

In another terminal ensure you have Node 24 (LTS) available.
Either use official packages or something like [`fnm`](https://github.com/Schniz/fnm).

Then cd to `/spa` and run

```bash
npm run build:watch
```

This will tell Vite to watch SPA source code and rebuild on every change. Docker will watch for changes in Vite's build directory and update the app.

You can now edit files in `/spa/src` with your IDE of choice (one with React and TypeScript support is strongly recommended, ie VSCode)

### Tests

From `/spa` run `npm run test`.
