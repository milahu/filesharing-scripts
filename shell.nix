{ pkgs ? import <nixpkgs> { }
  #pkgs ? import ./. {}
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    gnumake
    calibre
    (python3.withPackages (pp: with pp; [
      requests
      aiohttp
      beautifulsoup4
      mutagen # todo better https://github.com/quodlibet/mutagen/issues/651
      eyed3
      dateparser

      # fixme: this should be in pkgs.calibre.buildInputs
      mechanize
    ]))
  ] ++ pkgs.calibre.buildInputs;
}
