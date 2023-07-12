import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';
import { Account } from '../models/account';
import { MoneyPipe } from '../money.pipe';

@Component({
  selector: 'app-account-list',
  templateUrl: './account-list.component.html',
  styleUrls: ['./account-list.component.css']
})
export class AccountListComponent implements OnInit {
    accounts: Account[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'account';
    }

    ngOnInit() {
        this.ledgerService.getAccounts().subscribe(
            (accounts: Account[]) => this.accounts = accounts,
            (err: any) => console.log(err),
            () => console.log('All done getting accounts')
        );
    }

    activeAccounts(): Account[] {
        return this.accounts.filter(account => !account.closed_on);
    }

    inactiveAccounts(): Iterable<Account> {
        return this.accounts.filter(account => account.closed_on);
    }
}
