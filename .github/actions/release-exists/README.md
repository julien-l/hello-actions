To update `dist/index.js` (based on https://docs.github.com/en/actions/creating-actions/creating-a-javascript-action):

1. `asdf install` to install nodejs
2. `npm install` to install nodejs packages
3. `npx ncc build index.js --license licenses.txt` to update `dist/index.js`
