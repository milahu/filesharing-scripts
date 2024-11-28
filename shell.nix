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

      # FIXME these should be in pkgs.calibre.buildInputs
      mechanize
      msgpack
      lxml
      html5-parser
      pyqt6
      css-parser
      markdown
      html2text
    ]))
  ] ++ pkgs.calibre.buildInputs;
}
