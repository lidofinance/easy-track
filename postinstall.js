const path = require("path");
const copy = require("recursive-copy");

async function renameOpenzeppelinDependencies() {
  const nodeModulesPath = path.join(__dirname, "node_modules");
  const remapping = {
    "@openzeppelin/contracts": "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts",
  };

  for (const localPath of Object.keys(remapping)) {
    const from = path.join(nodeModulesPath, localPath);
    const to = path.join(nodeModulesPath, remapping[localPath]);
    try {
      console.log(`Move ${localPath} to ${remapping[localPath]}`);
      const res = await copy(from, to, {
        overwrite: true,
        expand: true,
        dot: true,
        junk: true,
      });
    } catch (error) {
      console.error(error);
      process.exit(1);
    }
  }
}

renameOpenzeppelinDependencies();
