# Automatic evaluation

This is short description with instruction notes how to create image to be upload to [grand-challenge.org](https://www.grand-challenge.org).
For newbies, please see [Get started with Docker](https://docs.docker.com/get-started).
First you need to install Docker.io and run everything as super user `sudo -i`.


## Build

Copy the required data to the local directory

```bash
docker build -t anhir -f Dockerfile .
```

## Run and Test

Run one of following sample registration experiments:
 * simulate the ideal registration, assuming having all landmarks
    ```bash
    python benchmark/bm_template.py \
        -c ~/Medical-data/dataset_ANHIR/images/dataset_medium.csv \
        -d ~/Medical-temp/dataset_ANHIR/images \
        -o ~/Medical-temp/experiments_anhir/ \
        --an_executable none
    python bm_experiments/bm_comp_perform.py -o ~/Medical-temp/experiments_anhir/BmTemplate
    # remove all registered images
    rm ~/Medical-temp/experiments_anhir/BmTemplate/*/*.jpg \
        ~/Medical-temp/experiments_anhir/BmTemplate/*/*.png
    ```
 * run bUnwarpJ in ImageJ registration on the real data
    ```bash
    python bm_experiments/bm_bunwarpj.py \
        -c ~/Medical-data/dataset_ANHIR/images/dataset_medium.csv \
        -d ~/Medical-temp/dataset_ANHIR/images \
        -o ~/Medical-temp/experiments_anhir/ \
        --run_comp_benchmark \
        -fiji ~/Applications/Fiji.app/ImageJ-linux64 \
        -config ./configs/ImageJ_bUnwarpJ_histo-1k.txt
    # remove all registered images
    rm ~/Medical-temp/experiments_anhir/BmUnwarpJ/*/*.jpg \
        ~/Medical-temp/experiments_anhir/BmUnwarpJ/*/*.png
    ```

Running the docker image with mapped folders 
```bash
mkdir submission output
```
and upload the sample submission to `submission` and run the image
```bash
docker run --rm -it \
        --memory=4g \
        -v $(pwd)/submission/:/input/ \
        -v $(pwd)/output/:/output/ \
        anhir
```


## Export 

Export the created image to be uploaded to the evaluation system.
```bash
docker save anhir > anhir.tar
```

## Browsing images

**Browsing**
To see your local biulded images use:
```bash
docker image ls
```

**Cleaning**
In case you fail with some builds, you may need to clean your local storage.
```bash
docker image prune
```
or [Docker - How to cleanup (unused) resources](https://gist.github.com/bastman/5b57ddb3c11942094f8d0a97d461b430)
```bash
docker images | grep "none"
docker rmi $(docker images | grep "none" | awk '/ / { print $3 }')
```


## References

* https://evalutils.readthedocs.io/en/latest/usage.html
* https://grand-challengeorg.readthedocs.io/en/latest/evaluation.html