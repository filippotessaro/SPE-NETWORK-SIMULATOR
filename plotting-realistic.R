library(plyr)
library(dplyr)
library(doMC)
library(ggplot2)
registerDoMC(cores=detectCores())

# indicates the results folder
folders <- c('./aloha-realistic','./trivial-realistic')

# Plotting Folder
res.folder = "./plot-realistic"
mainDir = "./"

# check if there is the data folders
if(FALSE){
    for (folder in folders){
        if(!dir.exists(file.path(mainDir, folder))){
            dir.create(file.path(mainDir, folder))
            print("No dir " + folder)
            print(folder + " created!")
        }
    }
}


#if not exist, create folder plot as output
ifelse(!dir.exists(file.path(mainDir, res.folder)), dir.create(file.path(mainDir, res.folder)), FALSE)

# Simulation Type
simType <- list('aloha-realistic','trivial-realistic')

# possible packet states
PKT_RECEIVING = 0
PKT_RECEIVED = 1
PKT_CORRUPTED = 2
PKT_GENERATED = 3
PKT_QUEUE_DROPPED = 4
PKT_CORRUPTED_BY_CHANNEL = 5

# determine whether a string contains a parsable number"
is.number <- function(string) {
    if (length(grep("^[[:digit:]]*$", string)) == 1)
    return (T)
    else
    return (F)
}

# gets the list of files with a certain prefix and suffix in a folder
get.data.files <- function(folder, suffix=".csv") {
    if (strsplit(suffix, '')[[1]][1] == '.')
    suffix <- paste('\\', suffix, sep='')
    return(list.files(folder, pattern=paste('.*', suffix, sep='')))
}

# splits the name of an output file by _ and extracts the values of simulation parameters
get.params <- function(filename, fields) {
    p <- strsplit(gsub(".csv", "", basename(filename)), "_")[[1]]
    #to add a column, we need to have something in the dataframe, so we add a
    #fake column which we remove at the end
    d <- data.frame(todelete=1)
    for (f in 1:length(fields)) {
        v <- p[f]
        if (is.number(v))
        d[[fields[[f]]]] <- as.numeric(v)
        else
        d[[fields[[f]]]] <- v
    }
    d$todelete <- NULL
    return (d)
}


# if there is no aggregated file, load all csv files into a single one
aggregated.file <- paste(res.folder, 'alld.Rdata', sep='/')

# Initialize dataframe
alld <- data.frame()
# find all csv in current folder
aggregated.file <- paste(res.folder, 'alld.Rdata', sep='/')
if (!file.exists(aggregated.file)) {
    for(i in folders){
        data.files <- get.data.files(i, '.csv')
        for (f in data.files) {
            full.path <- paste(i, f, sep='/')
            print(full.path)
            pars <- get.params(full.path, c('prefix', 'lambda', 'seed'))
            d <- read.csv(full.path)
            d <- cbind(d, pars)
            alld <- rbind(d, alld)
        }

        save(alld, file=aggregated.file)
    }
}else {
    # otherwise simply load the aggregated file
    load(aggregated.file)
}
print('End Loading files')

# computes the offered load
compute.offered.load <- function(d, data.rate, sim.time) {
    # keep generation events only
    d <- subset(d, event == PKT_GENERATED)
    offered.load <- ddply(d, c("src", "lambda"), function(x) {
        return(data.frame(ol=(sum(x$size * 8) / sim.time) / (1024**2)))
    }, .parallel=T)
    return(offered.load)
}

# computes the queue drop rate: dropped packets / generated packets
compute.drop.rate <- function(d, group=F) {
    fields <- c('lambda')
    if (!group)
    fields <- c('src', fields)
    drop.rate <- ddply(d, fields, function(x) {
        all.packets <- subset(x, event == PKT_GENERATED)
        lost.packets <- subset(x, event == PKT_QUEUE_DROPPED)
        return(data.frame(dr=nrow(lost.packets)/nrow(all.packets)))
    }, .parallel=T)
    return(drop.rate)
}

# computes collision rate: corrupter / (received + corrupted)
compute.collision.rate <- function(d, group=F) {
    fields <- c('lambda')
    if (!group)
    fields <- c('dst', fields)
    collision.rate <- ddply(d, fields, function(x) {
        all.packets <- subset(x, event == PKT_RECEIVED | event == PKT_CORRUPTED )
        lost.packets <- subset(all.packets, event == PKT_CORRUPTED )
        return(data.frame(cr=nrow(lost.packets)/nrow(all.packets)))
    }, .parallel=T)
    return(collision.rate)
}

# compute throughput: total bits received / simulation time
compute.throughput <- function(d, data.rate, sim.time, group=F) {
    fields <- c('lambda')
    if (!group)
    fields <- c('dst', fields)
    throughput <- ddply(d, fields, function(x) {
        received.packets <- subset(x, event == PKT_RECEIVED)
        return(data.frame(tr=sum(received.packets$size*8)/sim.time/(1024**2)))
    }, .parallel=T)
    return(throughput)
}

# total offered load in bits per second
offered.load <- function(lambda, n.nodes, packet.size=(1500+32)/2) {
    lambda*n.nodes*packet.size*8/1024/1024
}

# get simulation time and number of nodes from the simulation data
n.nodes <- length(unique(alld$src))

all.cr <- data.frame()
all.dr <- data.frame()
all.tr <- data.frame()
alldTemp <- data.frame()

j <- 1

# iterate over all the possible folders
while(j<=length(simType)){

    # filter over the simulation type
    alldTemp <- select(filter(alld, prefix == simType[[j]]),everything())

    # comupute the time of that simualtion
    sim.time <- max(alldTemp$time)

    # compute the statistics
    cr <- compute.collision.rate(alldTemp)
    cr$ol <- offered.load(cr$lambda, n.nodes=n.nodes)
    cr$prefix <-rep(simType[[j]] ,nrow(cr))

    # drop rate
    dr <- compute.drop.rate(alldTemp)
    dr$ol <- offered.load(dr$lambda, n.nodes=n.nodes)
    dr$prefix <-rep(simType[[j]] ,nrow(dr))

    # throughput
    tr <- compute.throughput(alldTemp, 8e6, sim.time)
    tr$ol <- offered.load(tr$lambda, n.nodes=n.nodes)
    tr$prefix <-rep(simType[[j]] ,nrow(tr))

    # store the results into the various general dataframe
    all.cr <- rbind(all.cr, cr)
    all.dr <- rbind(all.dr, dr)
    all.tr <- rbind(all.tr, tr)

    # increment counter
    j <- j + 1
}

print('End Quering, Start plotting')

# filter over the node number: 1
all.tr <- select(filter(all.tr, dst==9), everything())

# and plot the results
div <- 3
p <- ggplot(all.tr, aes(x=ol, y=tr, color=factor(prefix))) +
geom_line() +
geom_point() +
xlab('total offered load (Mbps)') +
ylab('throughput at receiver (Mbps)') +
labs(color="Test")

#ylim(c(0, 3))
ggsave(paste(res.folder, '/realistic-thr_', n.nodes, '.pdf', sep=''), width=16/div, height=9/div)
print(p)

all.cr <- select(filter(all.cr, dst==9),everything())
all.dr <- select(filter(all.dr, src==9), everything())

pcr <- ggplot(all.cr, aes(x=ol, y=cr, color=factor(prefix))) +
geom_line() +
geom_point() +
xlab('total offered load (Mbps)') +
ylab('packet collision rate at receiver') +
labs(color="receiver node")
#ylim(c(0, 1))
ggsave(paste(res.folder, '/realistic-pcr_', n.nodes, '.pdf', sep=''), width=16/div, height=9/div)
print(pcr)

pdr <- ggplot(all.dr, aes(x=ol, y=dr, color=factor(prefix))) +
geom_line() +
geom_point() +
xlab('total offered load (Mbps)') +
ylab('packet drop rate at sender') +
labs(color="sender node")
#ylim(c(0, 1))
ggsave(paste(res.folder, '/realistic-pdr_', n.nodes, '.pdf', sep=''), width=16/div, height=9/div)
print(pdr)
