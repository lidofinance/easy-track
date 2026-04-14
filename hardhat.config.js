// Brownie starts Hardhat as a subprocess for `*-fork` networks. Polling keeps
// Hardhat's file watcher predictable in that mode, especially when the process
// is owned by Brownie's Python wrapper instead of an interactive shell.
process.env.CHOKIDAR_USEPOLLING ??= "true";

module.exports = {
  networks: {
    hardhat: {
      allowUnlimitedContractSize: true,
      hardfork: "prague",
      // Brownie asks the forked Hardhat node to execute `eth_call`/trace requests
      // at the fork block. For custom chain ids Hardhat has no built-in
      // hardfork activation history, so Brownie-backed calls fail with:
      // "No known hardfork for execution on historical block ...".
      //
      // For the custom fork targets declared below, treating Prague as active
      // from genesis is enough for Brownie's forked calls.
      chains: {
        32382: {
          hardforkHistory: {
            prague: 0,
          },
        },
      },
      accounts: {
        mnemonic: "simple adjust essence unlock barely various poem basic sunny purchase carpet give",
      }
    },
  },
};
